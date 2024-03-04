import os
from time import sleep, time

from util.realistic_data.ingest.api_client import APIClient
from util.realistic_data.ingest.api_starter import APIStarter
from util.realistic_data.ingest.config import Config
from util.realistic_data.ingest.local_command_runner import LocalCommandRunner
from util.realistic_data.ingest.s3_interface import S3Interface
from util.realistic_data.ingest.ssh_handler import SSHHandler


def main():
    if Config.config.ssh.enabled:
        ssh = SSHHandler()
    else:
        local_commands = LocalCommandRunner()

    if Config.config.script_options.wipe_database:
        print("Wiping database")
        collection_names = ["channels", "experiments", "records"]
        if Config.config.ssh.enabled:
            ssh.drop_database_collections(collection_names)
        else:
            local_commands.drop_database_collections(collection_names)

    echo = S3Interface()
    if Config.config.script_options.wipe_echo:
        print(
            f"Wiping data stored in Echo, bucket: {Config.config.echo.storage_bucket}",
        )
        echo.delete_all()

    starter = APIStarter()
    api_url = f"http://{Config.config.api.host}:{Config.config.api.port}"
    print(f"API started on {api_url}")

    channel_manifest = echo.download_manifest_file()
    og_api = APIClient(api_url, starter.process)
    og_api.submit_manifest(channel_manifest)

    experiments_import = echo.download_experiments()
    if Config.config.ssh.enabled:
        ssh.transfer_experiments_file(experiments_import)
        ssh.import_experiments()
    else:
        local_commands.store_experiments_file(experiments_import)
        local_commands.import_experiments()
        sleep(2)

    hdf_page_iterator = echo.paginate_hdf_data()
    total_ingestion_start_time = time()

    for page in hdf_page_iterator:
        object_names = [hdf_file["Key"] for hdf_file in page["Contents"]]
        page_start_time = time()

        for name in object_names:
            hdf_file_dict = echo.download_hdf_file(name)
            og_api.submit_hdf(hdf_file_dict)

        page_end_time = time()
        page_duration = page_end_time - page_start_time
        print(f"Page ingestion duration: {page_duration:0.2f} seconds")
        og_api.refresh()

    total_ingestion_end_time = time()
    ingestion_duration = total_ingestion_end_time - total_ingestion_start_time
    print(f"Total ingestion duration: {ingestion_duration:0.2f} seconds")

    if Config.config.script_options.launch_api:
        starter.kill()


if __name__ == "__main__":
    main()
    # Script doesn't always exit once it's finished, this ensures it does
    os._exit(0)
