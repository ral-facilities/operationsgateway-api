from tempfile import SpooledTemporaryFile

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.mongo.interface import MongoDBInterface


class TestSubmitManifest:
    @pytest.mark.asyncio
    async def test_submit_manifest_success(
        self,
        test_app: TestClient,
        login_and_get_token,
        remove_manifest_fixture,
    ):
        with SpooledTemporaryFile(mode="w+b") as spooled_file:
            content = (
                '{"_id": "19000000000011", "channels": {"Test_image_1": {"name": "fancy'
                ' image tests part one", "path": "/test/image", "type": "image"}, '
                '"Test_image_2": {"name": "fancy image tests part two", "path": '
                '"/test/image", "type": "image"}}}'
            )
            spooled_file.write(content.encode())
            spooled_file.seek(0)

            files = {"file": ("sample_manifest.json", spooled_file, "application/json")}
            test_response = test_app.post(
                "/submit/manifest?bypass_channel_check=True",
                files=files,
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )

        assert test_response.status_code == 201
        response_data = test_response.json()
        assert response_data is not None

        test_dict = {
            "_id": "19000000000011",
            "channels": {
                "Test_image_1": {
                    "name": "fancy image tests part one",
                    "path": "/test/image",
                    "type": "image",
                },
                "Test_image_2": {
                    "name": "fancy image tests part two",
                    "path": "/test/image",
                    "type": "image",
                },
            },
        }

        new_manifest = await MongoDBInterface.find_one(
            "channels",
            filter_={"_id": response_data},
        )
        test_dict["_id"] = response_data
        assert new_manifest == test_dict

    @pytest.mark.asyncio
    async def test_submit_manifest_missing_file(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_response = test_app.post(
            "/submit/manifest",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 422
