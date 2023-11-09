import io

from fastapi.testclient import TestClient
import imagehash
from PIL import Image
import pytest

from test.conftest import set_preferred_colourmap, unset_preferred_colourmap


class TestGetImage:
    @pytest.mark.parametrize(
        "record_id, channel_name, original_image, use_preferred_colourmap,"
        "lower_level, upper_level, colourmap_name, expected_image_md5sum",
        [
            pytest.param(
                "20220408164136",
                "N_COMP_FF_IMAGE",
                True,
                False,
                None,
                None,
                None,
                "d6163f06fb03664a",
                id="Original image",
            ),
            pytest.param(
                "20220408002114",
                "N_LEG1_GREEN_NF_IMAGE",
                False,
                False,
                None,
                None,
                None,
                "879578586b6a6761",
                id="Image with default false colour settings",
            ),
            # repeat the above test but with the user's preferred colour map set to
            # check that the preference is used when no specific map is chosen
            pytest.param(
                "20220408002114",
                "N_LEG1_GREEN_NF_IMAGE",
                False,
                True,
                None,
                None,
                None,
                "87857858636b6763",
                id="Image using user's preferred colourmap",
            ),
            pytest.param(
                "20220408002114",
                "N_LEG1_GREEN_NF_IMAGE",
                None,
                False,
                50,
                200,
                "jet_r",
                "8f9438586a636b67",
                id="Image with all false colour params specified",
            ),
            # repeat the test above but with the user's preferred colour map set to
            # ensure that it is ignored and the specified colour map used
            pytest.param(
                "20220408002114",
                "N_LEG1_GREEN_NF_IMAGE",
                None,
                True,
                50,
                200,
                "jet_r",
                "8f9438586a636b67",
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
        expected_image_md5sum,
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
        assert expected_image_md5sum == image_checksum
