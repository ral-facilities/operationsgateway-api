import io

from fastapi.testclient import TestClient
import imagehash
from PIL import Image
import pytest

from test.conftest import (
    RECORD_ID_05_0803,
    set_preferred_float_colourmap,
    unset_preferred_float_colourmap,
)


class TestGetImage:
    @pytest.mark.parametrize(
        [
            "use_preferred_colourmap",
            "colourmap_name",
            "expected_image_phash",
        ],
        [
            pytest.param(
                False,
                None,
                "9b326c6930cf6798",
                id="Original image",
            ),
            pytest.param(
                True,
                None,
                "966939966562b665",
                id="Image using user's preferred colourmap",
            ),
            pytest.param(
                False,
                "berlin",
                "96493996656ab665",
                id="Image with all false colour params specified",
            ),
            pytest.param(
                True,
                "berlin",
                "96493996656ab665",
                id=(
                    "Image with all false colour params specified (ignoring "
                    "user's pref)"
                ),
            ),
        ],
    )
    def test_valid_get_image(
        self,
        test_app: TestClient,
        login_and_get_token: str,
        use_preferred_colourmap: bool,
        colourmap_name: str,
        expected_image_phash: str,
    ) -> None:
        set_preferred_float_colourmap(
            test_app,
            login_and_get_token,
            use_preferred_colourmap,
        )

        query_string = ""
        query_params_array = []
        if colourmap_name:
            query_params_array.append(f"colourmap_name={colourmap_name}")

        if len(query_params_array) > 0:
            query_string = "?" + "&".join(query_params_array)

        test_response = test_app.get(
            f"/images/float/{RECORD_ID_05_0803}/CM-202-CVC-WFS{query_string}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        unset_preferred_float_colourmap(
            test_app,
            login_and_get_token,
            use_preferred_colourmap,
        )

        assert test_response.status_code == 200, test_response.content.decode()
        bytes_image = test_response.content
        img = Image.open(io.BytesIO(bytes_image))
        image_checksum = str(imagehash.phash(img))
        img.save(image_checksum + ".png")
        assert expected_image_phash == image_checksum
