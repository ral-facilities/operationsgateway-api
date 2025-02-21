from fastapi.testclient import TestClient
import pytest

from test.conftest import set_preferred_colourmap, unset_preferred_colourmap


class TestGetImage:
    @pytest.mark.parametrize(
        [
            "record_id",
            "channel_name",
            "use_preferred_colourmap",
            "colourmap_name",
            "expected_image_phash",
        ],
        [
            pytest.param(
                "record_id",
                "channel_name",
                False,
                None,
                "8000000000000000",
                id="Original image",
            ),
            pytest.param(
                "record_id",
                "channel_name",
                True,
                None,
                "8000000000000000",
                id="Image using user's preferred colourmap",
            ),
            pytest.param(
                "record_id",
                "channel_name",
                False,
                "berlin",
                "8000000000000000",
                id="Image with all false colour params specified",
            ),
            pytest.param(
                "record_id",
                "channel_name",
                True,
                "berlin",
                "8000000000000000",
                id="Image with all false colour params specified (ignoring "
                "user's pref)",
            ),
        ],
    )
    def test_valid_get_image(
        self,
        test_app: TestClient,
        login_and_get_token: str,
        record_id: str,
        channel_name: str,
        use_preferred_colourmap: bool,
        colourmap_name: str,
        expected_image_phash: str,
    ) -> None:
        set_preferred_colourmap(test_app, login_and_get_token, use_preferred_colourmap)

        query_string = ""
        query_params_array = []
        if colourmap_name:
            query_params_array.append(f"colourmap_name={colourmap_name}")

        if len(query_params_array) > 0:
            query_string = "?" + "&".join(query_params_array)

        test_response = test_app.get(
            f"/images/nullable/{record_id}/{channel_name}{query_string}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        unset_preferred_colourmap(
            test_app,
            login_and_get_token,
            use_preferred_colourmap,
        )

        # TODO Cannot actually assert anything useful until we have simulated data from
        # EPAC
        # assert test_response.status_code == 200, test_response.content.decode()
        # bytes_image = test_response.content
        # img = Image.open(io.BytesIO(bytes_image))
        # image_checksum = str(imagehash.phash(img))
        # assert expected_image_phash == image_checksum
        assert test_response.status_code == 404, test_response.content.decode()
