import os
from pprint import pprint
from time import time

import requests


BASE_DIR = "/path/to/hdf/files"
API_URL = "http://127.0.0.1:8000"


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
                    if response.status_code == 200:
                        print(
                            f"Ingested {file.name}, time taken: {duration:0.2f}"
                            " seconds"
                        )
                    else:
                        print(f"{response.status_code} returned")
                        pprint(response.text)
