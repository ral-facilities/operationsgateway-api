import hashlib

from fastapi.testclient import TestClient
import pytest


class TestGetImage:
    @pytest.mark.parametrize(
        "record_id, channel_name, original_image, "
        "lower_level, upper_level, colourmap_name, expected_image_md5sum",
        [
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P1-CAM-1",
                True,
                None,
                None,
                None,
                "b9f3cbeda088a75d50df4c8476c59231",
                id="Original image",
            ),
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P2-CAM-1",
                False,
                None,
                None,
                None,
                "8d10c1b2f9a0f2945d8b853b990dcddf",
                id="Image with default false colour settings",
            ),
            pytest.param(
                "20230605100000",
                "FE-204-NSO-P2-CAM-1",
                None,
                50,
                200,
                "jet_r",
                "b36395bfadc73a8c4d1facc5204c25b0",
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
