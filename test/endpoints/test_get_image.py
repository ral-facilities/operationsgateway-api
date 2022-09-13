import base64
import hashlib
import json

from fastapi.testclient import TestClient
import pytest


class TestGetImage:
    @pytest.mark.parametrize(
        "record_id, channel_name, string_response, expected_image_md5sum",
        [
            pytest.param(
                "20220408164136",
                "N_COMP_FF_IMAGE",
                True,
                "9d2fc96084349c5bff10206ef4dfdf3e",
                id="Output as base64 string",
            ),
            pytest.param(
                "20220408002114",
                "N_LEG1_GREEN_NF_IMAGE",
                False,
                "47f2e189fcf44cffb010b72a6de153bd",
                id="Output as image",
            ),
            pytest.param(
                "20220408002114",
                "N_LEG1_GREEN_NF_IMAGE",
                None,
                "47f2e189fcf44cffb010b72a6de153bd",
                id="No string response query parameter",
            ),
        ],
    )
    def test_valid_get_image(
        self,
        test_app: TestClient,
        record_id,
        channel_name,
        string_response,
        expected_image_md5sum,
    ):
        string_response_param = (
            f"?string_response={json.dumps(string_response)}"
            if isinstance(string_response, bool)
            else ""
        )
        test_response = test_app.get(
            f"/images/{record_id}/{channel_name}{string_response_param}",
        )

        assert test_response.status_code == 200

        if string_response:
            assert isinstance(test_response.json(), str)
            bytes_image = base64.b64decode(test_response.json())

        else:
            assert isinstance(test_response.content, bytes)
            bytes_image = test_response.content

        image_checksum = hashlib.md5(bytes_image).hexdigest()  # noqa: S303
        assert expected_image_md5sum == image_checksum
