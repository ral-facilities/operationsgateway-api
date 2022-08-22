import argparse
import os
from pprint import pprint
import shutil
import socket
from subprocess import Popen, PIPE
from time import sleep, time

from motor.motor_asyncio import AsyncIOMotorClient
import requests

parser = argparse.ArgumentParser()
parser.add_argument(
    "-p",
    "--path",
    type=str,
    help="Base directory path containing HDF files to ingest",
    required=True,
)
parser.add_argument(
    "-u",
    "--url",
    type=str,
    help="URL of API to ingest files to",
    default=None,
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

# Put command line options into variables
args = parser.parse_args()
BASE_DIR = args.path
API_URL = args.url
WIPE_DATABASE = args.wipe_database
DATABASE_CONNECTION_URL = "mongodb://localhost:27017"
DATABASE_NAME = args.database_name
DELETE_IMAGES = args.delete_images
IMAGES_PATH = args.images_path


# Wipe collections in the database
if WIPE_DATABASE:
    client = AsyncIOMotorClient(DATABASE_CONNECTION_URL)
    db = client[DATABASE_NAME]

    records_drop = db.records.drop()
    print("Records collection dropped")
    waveforms_drop = db.waveforms.drop()
    print("Waveforms collection dropped")

# Delete images from disk
if DELETE_IMAGES:
    for root, dirs, files in os.walk(IMAGES_PATH):
        for f in files:
            os.unlink(os.path.join(root, f))
        print(f"Removed {len(files)} file(s) from base level of image path")

        for d in dirs:
            shutil.rmtree(os.path.join(root, d))
        print(f"Removed {len(dirs)} directorie(s) and their contents from image path")

def is_api_alive(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((host, int(port)))
        return True
    except Exception:
        return False

# Start API if an API URL isn't given as a command line option
if not args.url:
    host = "127.0.0.1"
    port = "8000"
    api_process = Popen(
        [
            "uvicorn",
            "operationsgateway_api.src.main:app",
            "--host",
            host,
            "--port",
            port,
        ],
        stdout=PIPE,
        stderr=PIPE,
    )

    print("Checking if API started")
    api_alive = False
    while not api_alive:
        api_alive = is_api_alive(host, port)
        sleep(1)
        print("API not started yet...")

    API_URL = f"http://{host}:{port}"
    print(f"API started on {API_URL}")

# Ingesting HDF files
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

# Kill API process if it was started in this script
# Using args.url because API_URL will be populated when API process was started
if not args.url:
    api_process.kill()
    print(f"API stopped on {API_URL}")
