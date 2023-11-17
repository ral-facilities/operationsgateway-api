import io

from fastapi.testclient import TestClient
import imagehash
from PIL import Image
import pytest

from test.conftest import set_preferred_colourmap, unset_preferred_colourmap


class TestGetImage:
    @pytest.mark.parametrize(
        "record_id, channel_name, original_image, use_preferred_colourmap,"
        "lower_level, upper_level, colourmap_name, expected_image_phash",
        [
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P1-CAM-1",
                True,
                False,
                None,
                None,
                None,
                "c8b624a4275e37b5",
                id="Original image",
            ),
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P2-CAM-1",
                False,
                False,
                None,
                None,
                None,
                "cd3331cc33cc6f0c",
                id="Image with default false colour settings",
            ),
            # repeat the above test but with the user's preferred colour map set to
            # check that the preference is used when no specific map is chosen
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P2-CAM-1",
                False,
                True,
                None,
                None,
                None,
                "cc3333c037cc338f",
                id="Image using user's preferred colourmap",
            ),
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P2-CAM-1",
                None,
                False,
                50,
                200,
                "jet_r",
                "8000000000000000",
                id="Image with all false colour params specified",
            ),
            # repeat the test above but with the user's preferred colour map set to
            # ensure that it is ignored and the specified colour map used
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P2-CAM-1",
                None,
                True,
                50,
                200,
                "jet_r",
                "8000000000000000",
                id="Image with all false colour params specified (ignoring "
                "user's pref)",
            ),
        ],
    )
    def test_valid_get_image(
        self,
        test_app: TestClient,
        login_and_get_token,
        record_id,
        channel_name,
        original_image,
        use_preferred_colourmap,
        lower_level,
        upper_level,
        colourmap_name,
        expected_image_phash,
    ):
        set_preferred_colourmap(test_app, login_and_get_token, use_preferred_colourmap)

        query_string = ""
        query_params_array = []

        if original_image is not None:
            # allow setting of "original_image=False"
            query_params_array.append(f"original_image={original_image}")
        if lower_level:
            query_params_array.append(f"lower_level={lower_level}")
        if upper_level:
            query_params_array.append(f"upper_level={upper_level}")
        if colourmap_name:
            query_params_array.append(f"colourmap_name={colourmap_name}")

        if len(query_params_array) > 0:
            query_string = "?" + "&".join(query_params_array)

        test_response = test_app.get(
            f"/images/{record_id}/{channel_name}{query_string}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        unset_preferred_colourmap(
            test_app,
            login_and_get_token,
            use_preferred_colourmap,
        )

        assert test_response.status_code == 200

        bytes_image = test_response.content
        img = Image.open(io.BytesIO(bytes_image))
        image_checksum = str(imagehash.phash(img))
        assert expected_image_phash == image_checksum
