import io
import json
from urllib.parse import quote

from fastapi.testclient import TestClient
import imagehash
from PIL import Image
import pytest


class TestGetImageFromFunction:
    @pytest.mark.parametrize(
        "record_id, function_name, functions, colourmap_name, expected_image_phash",
        [
            pytest.param(
                "20230605100000",
                "a",
                {"name": "a", "expression": "FE-204-NSO-P1-CAM-1 - 1"},
                None,
                "c8b624a4275637bd",
                id="Colormap undefined",
            ),
            pytest.param(
                "20230605100000",
                "a",
                {"name": "a", "expression": "FE-204-NSO-P1-CAM-1 - 1"},
                "jet_r",
                "b6b5db52d8b2c8a0",
                id="Colormap defined",
            ),
        ],
    )
    def test_valid_get_image(
        self,
        test_app: TestClient,
        login_and_get_token,
        record_id: str,
        function_name: str,
        functions: dict,
        colourmap_name: str,
        expected_image_phash: str,
    ):

        url = f"/images/function/{record_id}/{function_name}"
        url += f"?&functions={quote(json.dumps(functions))}"
        if colourmap_name is not None:
            url += f"&colourmap_name={colourmap_name}"

        test_response = test_app.get(
            url,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        bytes_image = test_response.content
        img = Image.open(io.BytesIO(bytes_image))
        image_checksum = str(imagehash.phash(img))
        assert expected_image_phash == image_checksum
