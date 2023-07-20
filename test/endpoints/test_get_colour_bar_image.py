import hashlib

from fastapi.testclient import TestClient
import pytest


class TestGetColourBarImage:
    @pytest.mark.parametrize(
        "lower_level, upper_level, colourmap_name, expected_response_code, "
        "expected_image_md5sum",
        [
            pytest.param(
                None,
                None,
                None,
                200,
                "f021d06017c69036b56ea8b7f415ce3c",
                id="Colour bar with default false colour settings",
            ),
            pytest.param(
                50,
                200,
                "jet_r",
                200,
                "011777b7f7ad385bbeaa0c7d80d99f7e",
                id="Colour bar with all false colour params specified",
            ),
            pytest.param(
                -1,
                None,
                None,
                422,  # pydantic error
                None,
                id="Client error due to lower_level not in range 1 to 255",
            ),
            pytest.param(
                None,
                300,
                None,
                422,  # pydantic error
                None,
                id="Client error due to upper_level not in range 1 to 255",
            ),
            pytest.param(
                100,
                50,
                None,
                400,  # custom error
                None,
                id="Client error due to lower_level being higher than upper_level",
            ),
            pytest.param(
                None,
                None,
                "non_existent_colourmap_name",
                400,  # custom error
                None,
                id="Client error due to colourmap_name not being valid",
            ),
        ],
    )
    def test_get_colour_bar_image(
        self,
        test_app: TestClient,
        login_and_get_token,
        lower_level,
        upper_level,
        colourmap_name,
        expected_response_code,
        expected_image_md5sum,
    ):
        query_string = ""
        query_params_array = []

        if lower_level:
            query_params_array.append(f"lower_level={lower_level}")
        if upper_level:
            query_params_array.append(f"upper_level={upper_level}")
        if colourmap_name:
            query_params_array.append(f"colourmap_name={colourmap_name}")

        if len(query_params_array) > 0:
            query_string = "?" + "&".join(query_params_array)

        print(f"query_string={query_string}")

        test_response = test_app.get(
            f"/images/colour_bar{query_string}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == expected_response_code

        if test_response.status_code == 200:
            bytes_image = test_response.content
            image_checksum = hashlib.md5(bytes_image).hexdigest()
            assert expected_image_md5sum == image_checksum
