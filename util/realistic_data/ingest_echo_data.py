from multiprocessing.pool import ThreadPool
import os
import threading
from time import time
from typing import List

from util.realistic_data.ingest.api_client import APIClient
from util.realistic_data.ingest.api_starter import APIStarter
from util.realistic_data.ingest.config import IngestEchoDataConfig
from util.realistic_data.ingest.database_operations import DatabaseOperations
from util.realistic_data.ingest.s3_interface import S3Interface


class DataIngester:
    def __init__(self) -> None:
        self.config = IngestEchoDataConfig()

    def download_and_ingest(
        self,
        object_names: List[str],
        s3_interface: S3Interface,
        api: APIClient,
    ) -> None:
        download_pool = ThreadPool(int(self.config.source.page_size))
        files = download_pool.map(s3_interface.download_hdf_file, object_names)

        ingest_pool = ThreadPool(int(self.config.api.gunicorn_num_workers))
        ingest_pool.map(api.submit_hdf, files)

    def main(self):
        mongodb = DatabaseOperations(connection_uri=self.config.database.connection_uri)
        echo = S3Interface(
            source_config=self.config.source,
            storage_bucket=self.config.api.storage_bucket,
            remote_experiments_file_path=self.config.database.remote_experiments_file_path,
        )

        if self.config.script_options.wipe_database:
            print("Wiping database")
            collection_names = ["channels", "experiments", "records"]
            mongodb.drop_collections(collection_names)

        echo.download_experiments()
        mongodb.import_data(
            self.config.database.remote_experiments_file_path,
            "experiments",
        )

        if self.config.script_options.wipe_echo:
            print(f"Wiping Echo bucket: {self.config.api.storage_bucket}")
            echo.delete_all()

        if self.config.script_options.import_users:
            print("Importing test users to the database")
            mongodb.import_data(self.config.database.test_users_file_path, "users")

        starter = APIStarter(
            launch_api=self.config.script_options.launch_api,
            api_config=self.config.api,
        )
        protocol = "https" if self.config.api.https else "http"
        api_url = f"{protocol}://{self.config.api.host}:{self.config.api.port}"
        print(f"API started on {api_url}")

        channel_manifest = echo.download_manifest_file()
        og_api = APIClient(
            url=api_url,
            username=self.config.api.username,
            password=self.config.api.password,
            process=starter.process,
        )
        og_api.submit_manifest(channel_manifest)

        hdf_page_iterator = echo.paginate_hdf_data()
        total_ingestion_start_time = time()

        last_successful_file = self.config.script_options.file_to_restart_ingestion
        ingestion_started = False if last_successful_file else True

        for page in hdf_page_iterator:
            object_names = [hdf_file["Key"] for hdf_file in page["Contents"]]
            page_start_time = time()

            if last_successful_file in object_names:
                print(f"Last successful file found: {last_successful_file}")
                ingestion_started = True

            if ingestion_started:
                if self.config.script_options.ingest_mode == "sequential":
                    for name in object_names:
                        hdf_file_dict = echo.download_hdf_file(name)
                        og_api.submit_hdf(hdf_file_dict)
                elif self.config.script_options.ingest_mode == "parallel":
                    self.download_and_ingest(object_names, echo, og_api)
            else:
                print(
                    f"Last successful file not found in page, skipping: {object_names}",
                )
                if og_api.process:
                    # Flushing stdout buffer so it doesn't become full,
                    # causing the script to hang
                    t = threading.Thread(
                        target=APIStarter.clear_buffers,
                        args=(og_api.process,),
                    )
                    t.start()

            page_end_time = time()
            page_duration = page_end_time - page_start_time
            print(f"Page ingestion duration: {page_duration:0.2f} seconds")
            og_api.refresh()

        total_ingestion_end_time = time()
        ingestion_duration = total_ingestion_end_time - total_ingestion_start_time
        print(f"Total ingestion duration: {ingestion_duration:0.2f} seconds")

        if self.config.script_options.launch_api:
            starter.kill()


if __name__ == "__main__":
    data_ingester = DataIngester()
    data_ingester.main()
    # Script doesn't always exit once it's finished, this ensures it does
    os._exit(0)
