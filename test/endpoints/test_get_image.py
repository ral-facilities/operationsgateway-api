import hashlib

from fastapi.testclient import TestClient
import pytest


class TestGetImage:
    @pytest.mark.parametrize(
        "record_id, channel_name, original_image, "
        "lower_level, upper_level, colourmap_name, expected_image_md5sum",
        [
            pytest.param(
                "20220408164136",
                "N_COMP_FF_IMAGE",
                True,
                None,
                None,
                None,
                "9d2fc96084349c5bff10206ef4dfdf3e",
                id="Original image",
            ),
            pytest.param(
                "20220408002114",
                "N_LEG1_GREEN_NF_IMAGE",
                False,
                None,
                None,
                None,
                "97a854f18ef539f443a39c091c88df29",
                id="Image with default false colour settings",
            ),
            pytest.param(
                "20220408002114",
                "N_LEG1_GREEN_NF_IMAGE",
                None,
                50,
                200,
                "jet_r",
                "707c50d0784e305f0f6d20fe39c93162",
                id="Image with all false colour params specified",
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
        lower_level,
        upper_level,
        colourmap_name,
        expected_image_md5sum,
    ):
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

        assert test_response.status_code == 200

        bytes_image = test_response.content

        image_checksum = hashlib.md5(bytes_image).hexdigest()
        assert expected_image_md5sum == image_checksum
