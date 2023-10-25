import hashlib

from fastapi.testclient import TestClient
import pytest

from test.conftest import set_preferred_colourmap, unset_preferred_colourmap


class TestGetColourBarImage:
    @pytest.mark.parametrize(
        "lower_level, upper_level, colourmap_name, use_preferred_colourmap,"
        "expected_response_code, expected_image_md5sum",
        [
            pytest.param(
                None,
                None,
                None,
                False,
                200,
                "d702de874316fb6787e9d6a2365e5f9e",
                id="Colour bar with default false colour settings",
            ),
            pytest.param(
                None,
                None,
                None,
                True,
                200,
                "b9ba6992a0f922e85ba871acd9f292e0",
                id="Colour bar using user's preferred colour map",
            ),
            pytest.param(
                50,
                200,
                "jet_r",
                False,
                200,
                "a805bd0e5ea33a1764194412673855c0",
                id="Colour bar with all false colour params specified",
            ),
            # repeat the test above but with the user's preferred colour map set to
            # ensure that it is ignored and the specified colour map used
            pytest.param(
                50,
                200,
                "jet_r",
                True,
                200,
                "a805bd0e5ea33a1764194412673855c0",
                id="Colour bar with all false colour params specified (ignoring "
                "user's pref)",
            ),
            pytest.param(
                -1,
                None,
                None,
                False,
                422,  # pydantic error
                None,
                id="Client error due to lower_level not in range 1 to 255",
            ),
            pytest.param(
                None,
                300,
                None,
                False,
                422,  # pydantic error
                None,
                id="Client error due to upper_level not in range 1 to 255",
            ),
            pytest.param(
                100,
                50,
                None,
                False,
                400,  # custom error
                None,
                id="Client error due to lower_level being higher than upper_level",
            ),
            pytest.param(
                None,
                None,
                "non_existent_colourmap_name",
                False,
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
        use_preferred_colourmap,
        expected_response_code,
        expected_image_md5sum,
    ):
        set_preferred_colourmap(test_app, login_and_get_token, use_preferred_colourmap)

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

        unset_preferred_colourmap(
            test_app,
            login_and_get_token,
            use_preferred_colourmap,
        )

        assert test_response.status_code == expected_response_code

        if test_response.status_code == 200:
            bytes_image = test_response.content
            image_checksum = hashlib.md5(bytes_image).hexdigest()
            assert expected_image_md5sum == image_checksum
