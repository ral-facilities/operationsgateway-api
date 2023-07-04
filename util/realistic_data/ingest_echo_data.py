from multiprocessing.pool import ThreadPool
from time import time
from typing import List

from util.realistic_data.ingest.api_client import APIClient
from util.realistic_data.ingest.api_starter import APIStarter
from util.realistic_data.ingest.config import Config
from util.realistic_data.ingest.s3_interface import S3Interface
from util.realistic_data.ingest.ssh_handler import SSHHandler


def download_and_ingest(object_names: List[str], s3_interface: S3Interface, api: APIClient):
    download_pool = ThreadPool(int(Config.config.echo.page_size))
    files = download_pool.map(s3_interface.download_hdf_file, object_names)
    
    ingest_pool = ThreadPool(int(Config.config.api.gunicorn_num_workers))
    ingest_pool.map(api.submit_hdf, files)


def main():
    ssh = SSHHandler()
    if Config.config.script_options.wipe_database:        
        collection_names = ["channels", "experiments", "records", "waveforms"]
        ssh.drop_database_collections(collection_names)
    
    if Config.config.script_options.delete_images:
        pass

    starter = APIStarter()
    api_url = f"http://{Config.config.api.host}:{Config.config.api.port}"
    print(f"API started on {api_url}")

    echo = S3Interface()
    channel_manifest = echo.download_manifest_file()
    og_api = APIClient(api_url)
    og_api.submit_manifest(channel_manifest)

    experiments_import = echo.download_experiments()
    ssh.transfer_experiments_file(experiments_import)
    ssh.import_experiments()

    hdf_page_iterator = echo.paginate_hdf_data()
    total_ingestion_start_time = time()

    for page in hdf_page_iterator:
        object_names = [hdf_file["Key"] for hdf_file in page["Contents"]]
        page_start_time = time()

        download_and_ingest(object_names, echo, og_api)

        page_end_time = time()
        page_duration = page_end_time - page_start_time
        print(f"Page ingestion duration: {page_duration:0.2f} seconds")
    
    total_ingestion_end_time = time()
    ingestion_duration = total_ingestion_end_time - total_ingestion_start_time
    print(f"Total ingestion duration: {ingestion_duration:0.2f} seconds")

    if not Config.config.script_options.launch_api:
        starter.kill()


if __name__ == "__main__":
    main()
