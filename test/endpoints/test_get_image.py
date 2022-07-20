import base64
import io
import json

from fastapi.testclient import TestClient
from PIL import Image
import pytest


class TestGetImage:
    @pytest.mark.parametrize(
        "shot_number, channel_name, string_response, expected_image_size",
        [
            pytest.param(
                366375,
                "N_COMP_FF_IMAGE",
                True,
                (656, 494),
                id="Output as base64 string",
            ),
            pytest.param(
                366280,
                "N_LEG1_GREEN_NF_IMAGE",
                False,
                (401, 401),
                id="Output as image",
            ),
            pytest.param(
                366280,
                "N_LEG1_GREEN_NF_IMAGE",
                None,
                (401, 401),
                id="No string response query parameter",
            ),
        ],
    )
    def test_valid_get_image(
        self,
        test_app: TestClient,
        shot_number,
        channel_name,
        string_response,
        expected_image_size,
    ):
        string_response_param = (
            f"?string_response={json.dumps(string_response)}"
            if isinstance(string_response, bool)
            else ""
        )
        test_response = test_app.get(
            f"/images/{shot_number}/{channel_name}{string_response_param}",
        )

        assert test_response.status_code == 200

        # Storing expected image files and base64 strings would bloat the tests, so we
        # check whether the image is genuine (by opening using Pillow) and if it matches
        # an expected resolution
        if string_response:
            assert isinstance(test_response.json(), str)
            bytes_image = base64.b64decode(test_response.json())

        else:
            assert isinstance(test_response.content, bytes)
            bytes_image = test_response.content

        # If no exception is raised during opening via Pillow, we can check the size is
        # what's expected and then assume this is a good image
        image = Image.open(io.BytesIO(bytes_image))
        assert image.size == expected_image_size
