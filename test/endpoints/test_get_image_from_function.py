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
                "20220408164136",
                "a",
                {"name": "a", "expression": "N_COMP_FF_IMAGE + 10"},
                None,
                "ce3831cece3131ce",
                id="Colormap undefined",
            ),
            pytest.param(
                "20220408164136",
                "a",
                {"name": "a", "expression": "N_COMP_FF_IMAGE + 10"},
                "jet_r",
                "ce3831cfce313899",
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
