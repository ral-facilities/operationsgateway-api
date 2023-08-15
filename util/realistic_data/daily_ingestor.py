import argparse
from datetime import datetime
import os
from pathlib import Path
from pprint import pprint

from dateutil import tz
from util.realistic_data.ingest.api_client import APIClient


def main():
    print(f"Current datetime: {datetime.now()}")
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data-directory", type=str, required=True)
    parser.add_argument("-u", "--url", type=str, required=True)
    parser.add_argument("-f", "--failed-ingests-directory", required=True)
    args = parser.parse_args()

    hdf_data_directory = args.data_directory
    og_api_url = args.url
    failed_ingests_directory = args.failed_ingests_directory

    hdf_files = sorted(Path(hdf_data_directory).iterdir(), key=os.path.getmtime)

    hdf_file_date_format = "%Y-%m-%dT%H%M"
    hdf_file_dates = {
        file: datetime.strptime(file.name.split(".")[0], hdf_file_date_format).replace(
            tzinfo=tz.gettz("Europe/London"),
        )
        for file in hdf_files
    }
    files_to_ingest = []
    for file_path, file_datetime in hdf_file_dates.items():
        if file_datetime < datetime.now(tz=tz.gettz("Europe/London")):
            files_to_ingest.append(file_path)

    print("Files to ingest:")
    pprint([file.name for file in files_to_ingest])

    og_api = APIClient(og_api_url)

    for file_to_ingest in files_to_ingest:
        with open(file_to_ingest, "rb") as hdf_file:
            response_code = og_api.submit_hdf({file_to_ingest.name: hdf_file})

        if response_code == 201 or response_code == 200:
            print(
                f"Successfully ingested ({response_code}) '{file_to_ingest.name}'."
                " HDF file will be deleted",
            )
            file_to_ingest.unlink(missing_ok=True)
        else:
            print(
                f"Ingestion unsuccessful for: {file_to_ingest.name},"
                f" Response: {response_code}. Moving this file to so it can be"
                f" investigated by a human: {failed_ingests_directory}",
            )

            file_to_ingest.rename(f"{failed_ingests_directory}/{file_to_ingest.name}")


if __name__ == "__main__":
    main()
