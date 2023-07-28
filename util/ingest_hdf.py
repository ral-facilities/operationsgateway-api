import argparse
import json
import os
from pathlib import Path
from pprint import pprint
import socket
from subprocess import PIPE, Popen
import sys
import threading
from time import sleep, time

import boto3
from motor.motor_asyncio import AsyncIOMotorClient
import requests

from operationsgateway_api.src.config import Config

parser = argparse.ArgumentParser()
parser.add_argument(
    "-U",
    "--username",
    type=str,
    help="Username of a user that has permissions to call the /submit/hdf endpoint",
    required=True,
)
parser.add_argument(
    "-P",
    "--password",
    type=str,
    help="Password of the user specified by the -U/--username argument",
    required=True,
)
parser.add_argument(
    "-p",
    "--path",
    type=str,
    help="Base directory path containing HDF files to ingest. HDF files should be"
    " stored in subdirectories - no files will be detected in the base directory of the"
    " path given. The channel manifest file should be present in the base directory and"
    " must be called 'channel_manifest.json'.",
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
    "-e",
    "--experiments",
    help="Flag to determine whether stored experiments should be deleted & re-ingested",
    action="store_true",
    default=False,
)

# Put command line options into variables
args = parser.parse_args()
USERNAME = args.username
PASSWORD = args.password
BASE_DIR = args.path
API_URL = args.url
WIPE_DATABASE = args.wipe_database
DATABASE_CONNECTION_URL = "mongodb://localhost:27017"
DATABASE_NAME = args.database_name
DELETE_IMAGES = args.delete_images
BUCKET_NAME = Config.config.images.image_bucket_name
REINGEST_EXPERIMENTS = args.experiments


# Wipe collections in the database
if WIPE_DATABASE:
    client = AsyncIOMotorClient(DATABASE_CONNECTION_URL)
    db = client[DATABASE_NAME]

    records_drop = db.records.drop()
    print("Records collection dropped")
    waveforms_drop = db.waveforms.drop()
    print("Waveforms collection dropped")
    if REINGEST_EXPERIMENTS:
        experiments_drop = db.experiments.drop()
        print("Experiments collection dropped")

# Delete images from S3 object storage
if DELETE_IMAGES:
    s3_resource = boto3.resource(
        "s3",
        endpoint_url=Config.config.images.echo_url,
        aws_access_key_id=Config.config.images.echo_access_key,
        aws_secret_access_key=Config.config.images.echo_secret_key,
    )


    bucket = s3_resource.Bucket(BUCKET_NAME)
    print(f"Retrieved '{BUCKET_NAME}' bucket, going to delete all files in the bucket")
    bucket.objects.all().delete()
    print(f"Remove all files from the '{BUCKET_NAME}' bucket")



def is_api_alive(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((host, int(port)))
        return True
    except Exception:
        return False


def clear_buffers(process, output=False):
    out = process.stdout.read()
    err = process.stderr.read()
    if output:
        print(out.decode("utf-8"))
        print(err.decode("utf-8"))


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
            "--log-config",
            str(Path(__file__).parent.parent / "operationsgateway_api/logging.ini"),
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
        # Check for the return code to see if the API started successfully
        api_process.poll()
        if api_process.returncode is not None and api_process.returncode != 0:
            t = threading.Thread(target=clear_buffers, args=(api_process, True))
            t.start()
            sys.exit("API has failed to start up, please see output above")

    API_URL = f"http://{host}:{port}"
    print(f"API started on {API_URL}")

# Login to get an access token
print(f"Login as '{USERNAME}' to get access token")
credentials_json = json.dumps({"username": USERNAME, "password": PASSWORD})
response = requests.post(
    f"{API_URL}/login",
    data=credentials_json,
)
# strip the first and last characters off the response
# (the double quotes that surround it)
token = response.text[1:-1]


# Ingesting channel manifest file
with open(f"{BASE_DIR}/channel_manifest.json", "r") as channel_manifest:
    response = requests.post(
        f"{API_URL}/submit/manifest",
        files={"file": channel_manifest.read()},
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code == 201:
        print(f"Ingested channel manifest file, ID: {response.json()}")
    else:
        print(f"{response.status_code} returned")
        pprint(response.text)

# Ingesting HDF files
for entry in sorted(os.scandir(BASE_DIR), key=lambda e: e.name):
    if entry.is_dir():
        print(f"Iterating through {entry.path}")
        directory_start_time = time()
        for file in sorted(os.scandir(entry.path), key=lambda e: e.name):
            if file.name.endswith(".h5"):
                start_time = time()
                # Flushing stdout buffer so it doesn't become full, causing the script
                # to hang
                t = threading.Thread(target=clear_buffers, args=(api_process,))
                t.start()

                with open(file.path, "rb") as hdf_upload:
                    response = requests.post(
                        f"{API_URL}/submit/hdf",
                        files={"file": hdf_upload.read()},
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    end_time = time()
                    duration = end_time - start_time
                    if response.status_code == 201:
                        print(
                            f"Ingested {file.name}, time taken: {duration:0.2f}"
                            " seconds",
                        )
                    elif response.status_code == 200:
                        print(
                            f"Updated {file.name}, time taken: {duration:0.2f}"
                            " seconds",
                        )
                    else:
                        print(f"{response.status_code} returned")
                        pprint(response.text)
        directory_end_time = time()
        directory_duration = directory_end_time - directory_start_time
        
        print(
            f"Ingestion of {entry.path} complete, time taken:"
            f" {directory_duration:0.2f} seconds",
        )

# Getting experiments from Scheduler and storing them in the database
if REINGEST_EXPERIMENTS:
    response = requests.post(
        f"{API_URL}/experiments",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code == 200:
        print(
            f"Ingested {len(response.json())} experiments from Scheduler. Response from"
            " API call:",
        )
        pprint(response.json())
    else:
        print(f"{response.status_code} returned")
        pprint(response.text)

# Kill API process if it was started in this script
# Using args.url because API_URL will be populated when API process was started
if not args.url:
    api_process.kill()
    print(f"API stopped on {API_URL}")
