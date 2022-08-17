import argparse
import os
from pprint import pprint
from time import time

import requests


BASE_DIR = "/path/to/hdf/files"
API_URL = "http://127.0.0.1:8000"

parser = argparse.ArgumentParser()
parser.add_argument(
    "-p",
    "--path",
    type=str,
    help="Base directory path containing HDF files to ingest",
    required=True,
)
parser.add_argument("-u",
    "--url",
    type=str,
    help="URL of API to ingest files to",
    default="http://127.0.0.1:8000",
)
parser.add_argument(
    "-w",
    "--wipe-database",
    help="Flag to determine whether the database should be wiped before ingestion",
    action="store_true",
    default=False,
)
parser.add_argument(
    "-n",
    "--database-name",
    type=str,
    help="Name of database, used when wiping database before ingestion",
    default="opsgateway",
)
parser.add_argument(
    "-d",
    "--delete-images",
    help="Flag to determine whether to delete stored images before ingestion",
    action="store_true",
    default=False,
)
parser.add_argument(
    "-i",
    "--images-path",
    type=str,
    help="Image storage path, used when deleting images before ingestion",
    default=None,
)

args = parser.parse_args()
BASE_DIR = args.path
API_URL = args.url
WIPE_DATABASE = args.wipe_database
DATABASE_NAME = args.database_name
DELETE_IMAGES = args.delete_images
IMAGES_PATH = args.images_path


for entry in sorted(os.scandir(BASE_DIR), key=lambda e: e.name):
    if entry.is_dir():
        print(f"Iterating through {entry.path}")
        for file in sorted(os.scandir(entry.path), key=lambda e: e.name):
            if file.name.endswith(".h5"):
                start_time = time()
                with open(file.path, "rb") as hdf_upload:
                    response = requests.post(
                        f"{API_URL}/submit_hdf",
                        files={"file": hdf_upload.read()},
                    )

                    end_time = time()
                    duration = end_time - start_time
                    if response.status_code == 201:
                        print(
                            f"Ingested {file.name}, time taken: {duration:0.2f}"
                            " seconds"
                        )
                    elif response.status_code == 200:
                        print(
                            f"Updated {file.name}, time taken: {duration:0.2f}"
                            " seconds"
                        )
                    else:
                        print(f"{response.status_code} returned")
                        pprint(response.text)
