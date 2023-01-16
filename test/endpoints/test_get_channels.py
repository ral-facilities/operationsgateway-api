import json
import os

from fastapi.testclient import TestClient


class TestGetChannels:
    def test_get_channels(self, test_app: TestClient, login_and_get_token):
        test_response = test_app.get(
            "/channels",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        manifest_file_response = test_response.json()

        # A KeyError will be raised if there's no ID, thereby testing that an ID is
        # present. We can't test the value itself as it will change each time the test
        # executed
        del manifest_file_response["_id"]

        with open(
            f"{os.path.dirname(os.path.realpath(__file__))}/test_manifest.json",
            "r",
        ) as f:
            assert manifest_file_response == json.load(f)
