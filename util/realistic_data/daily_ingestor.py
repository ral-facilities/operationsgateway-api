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
        # Includes files only, any directories are ignored
        if file.is_file()
    }

    in_progress_date_format = f"{hdf_file_date_format}%S"
    current_datetime = (
        datetime.now().replace(microsecond=0).strftime(in_progress_date_format)
    )
    in_progress_dir = Path(f"{hdf_data_directory}/in_progress_{current_datetime}")
    in_progress_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created {in_progress_dir} directory")

    files_to_ingest = []
    for file_path, file_datetime in hdf_file_dates.items():
        if file_datetime < datetime.now(tz=tz.gettz("Europe/London")):
            # Move the file to an 'in progress' directory to avoid collisions with other
            # instances of this script (i.e. cron job every minute)
            try:
                # Updating `file_path` so the change in directory is captured when the
                # file is opened later in the script
                file_path = file_path.rename(
                    f"{in_progress_dir}/{file_path.name}",
                )
            except FileNotFoundError as e:
                print(e)
            else:
                files_to_ingest.append(file_path)

    print("Files to ingest:")
    pprint([file.name for file in files_to_ingest])

    try:
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
                try:
                    file_to_ingest.rename(
                        f"{failed_ingests_directory}/{file_to_ingest.name}",
                    )
                except FileNotFoundError as e:
                    print(e)
    except Exception as e:
        print(e)
    finally:
        # For any files that are left in the 'in progress' directory (perhaps due to an
        # issue such as login failure) move them back to the original directory to be
        # picked up by a future execution of this script
        in_progress_files = Path(in_progress_dir).iterdir()
        for file in in_progress_files:
            try:
                file.rename(f"{hdf_data_directory}/{file.name}")
            except FileNotFoundError as e:
                print(e)
            else:
                print(f"{file} moved back to data directory")

        # Clean up the 'in progress' directory
        print(f"Going to remove: {in_progress_dir}")
        Path.rmdir(in_progress_dir)


if __name__ == "__main__":
    main()
