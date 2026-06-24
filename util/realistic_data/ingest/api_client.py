from io import BytesIO
import json
from pprint import pprint
import threading
from time import time
from typing import Dict

import requests
from requests.exceptions import ConnectionError
from util.realistic_data.ingest.api_starter import APIStarter
from util.realistic_data.ingest.config import Config


class APIClient:
    def __init__(self, url: str, process=None) -> None:
        self.url = url
        self.access_token, self.refresh_token = self.login()
        self.process = process

    def login(self) -> str:
        # Login to get an access token
        print(f"Login as '{Config.config.api.username}' to get access token")

        endpoint = "/login"
        credentials_json = json.dumps(
            {
                "username": Config.config.api.username,
                "password": Config.config.api.password,
            },
        )
        try:
            response = requests.post(
                f"{self.url}{endpoint}",
                data=credentials_json,
            )

            # strip the first and last characters off the response
            # (the double quotes that surround it)
            access_token = response.text[1:-1]

            cookie_header = response.headers["set-cookie"]
            refresh_token = cookie_header.split("=")[1].split(";")[0]

            return access_token, refresh_token
        except ConnectionError:
            print(f"Cannot connect with API at {self.url} for {endpoint}")
        except requests.exceptions.InvalidSchema:
            print(
                "Invalid schema when logging in with requests. Have you added"
                " http/https to the start of the API URL?",
            )

    def refresh(self) -> str:
        print(f"Refresh token as '{Config.config.api.username}'")

        endpoint = "/refresh"

        try:
            response = requests.post(
                f"{self.url}{endpoint}",
                data=json.dumps({"token": f"{self.access_token}"}),
                headers={"Cookie": f"refresh_token={self.refresh_token}"},
            )
            self.access_token = response.text[1:-1]

        except ConnectionError:
            print(f"Cannot connect with API at {self.url} for {endpoint}")

    def submit_manifest(self, manifest_bytes: BytesIO) -> None:
        endpoint = "/submit/manifest"
        try:
            response = requests.post(
                f"{self.url}{endpoint}",
                files={"file": manifest_bytes.read()},
                headers={"Authorization": f"Bearer {self.access_token}"},
            )

            if response.status_code == 201:
                print(f"Ingested channel manifest file, ID: {response.json()}")
            else:
                print(f"{response.status_code} returned")
                pprint(response.text)
        except ConnectionError:
            print(f"Cannot connect with API at {self.url} for {endpoint}")

    def submit_hdf(self, hdf_file: Dict[str, BytesIO]) -> int:
        if self.process:
            # Flushing stdout buffer so it doesn't become full, causing the script
            # to hang
            t = threading.Thread(target=APIStarter.clear_buffers, args=(self.process,))
            t.start()

        endpoint = "/submit/hdf"
        filename, file = list(hdf_file.items())[0]
        ingest_start_time = time()
        try:
            response = requests.post(
                f"{self.url}{endpoint}",
                files={"file": file.read()},
                headers={"Authorization": f"Bearer {self.access_token}"},
            )

            ingest_end_time = time()

            duration = ingest_end_time - ingest_start_time
            if response.status_code == 201:
                print(f"Ingested {filename}, time taken: {duration:0.2f} seconds")
                return 201
            elif response.status_code == 200:
                print(f"Updated {filename}, time taken: {duration:0.2f} seconds")
                return 200
            else:
                print(f"{response.status_code} returned")
                pprint(response.text)
                return response.status_code
        except ConnectionError:
            print(f"Cannot connect with API at {self.url} for {endpoint}")
