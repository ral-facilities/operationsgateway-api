from io import BytesIO
import json
from pprint import pprint
from time import time
from typing import Dict

import requests
from util.realistic_data.ingest.config import Config


class APIClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self.token = self.login()

    def login(self) -> str:
        # Login to get an access token
        print(f"Login as '{Config.config.api.username}' to get access token")
        credentials_json = json.dumps(
            {
                "username": Config.config.api.username,
                "password": Config.config.api.password,
            },
        )
        response = requests.post(
            f"{self.url}/login",
            data=credentials_json,
        )
        # strip the first and last characters off the response
        # (the double quotes that surround it)
        token = response.text[1:-1]
        return token

    def submit_manifest(self, manifest_bytes: BytesIO) -> None:
        response = requests.post(
            f"{self.url}/submit/manifest",
            files={"file": manifest_bytes.read()},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if response.status_code == 201:
            print(f"Ingested channel manifest file, ID: {response.json()}")
        else:
            print(f"{response.status_code} returned")
            pprint(response.text)

    def submit_hdf(self, hdf_file: Dict[str, BytesIO]) -> None:
        filename, file = list(hdf_file.items())[0]
        ingest_start_time = time()
        response = requests.post(
            f"{self.url}/submit/hdf",
            files={"file": file.read()},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        ingest_end_time = time()

        duration = ingest_end_time - ingest_start_time
        if response.status_code == 201:
            print(f"Ingested {filename}, time taken: {duration:0.2f}" " seconds")
        elif response.status_code == 200:
            print(f"Updated {filename}, time taken: {duration:0.2f}" " seconds")
        else:
            print(f"{response.status_code} returned")
            pprint(response.text)
