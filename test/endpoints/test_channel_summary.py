import base64
import io

from fastapi.testclient import TestClient
import imagehash
from PIL import Image
import pytest

from test.conftest import (
    DATETIME_STR_05_0800,
    DATETIME_STR_05_0803,
    DATETIME_STR_05_1700,
    DATETIME_STR_06_1200,
    set_preferred_colourmap,
    set_preferred_float_colourmap,
    unset_preferred_colourmap,
    unset_preferred_float_colourmap, MARK_GEMINI_TEST,
)


class TestChannelSummary:
    @pytest.mark.parametrize(
        "channel_name, expected_summary",
        [
            pytest.param(
                "SER-202-BI-RH-1",
                {
                    "first_date": DATETIME_STR_05_0800,
                    "most_recent_date": DATETIME_STR_06_1200,
                    "recent_sample": [
                        {DATETIME_STR_06_1200: 48.761769913881054},
                        {DATETIME_STR_05_1700: 44.550989418488655},
                        {DATETIME_STR_05_0803: 40.81474627800218},
                    ],
                },
                id="Scalar channel (number) summary",
            ),
        ],
    )
    def test_valid_scalar_channel_summary(
        self,
        test_app: TestClient,
        login_and_get_token,
        channel_name,
        expected_summary,
    ):
        test_response = test_app.get(
            f"/channels/summary/{channel_name}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        assert test_response.json() == expected_summary

    @pytest.mark.parametrize(
        "channel_name, expected_summary",
        [
            pytest.param(
                "ASTRA_CONTROL_MODE_STRING",
                {
                    "first_date": DATETIME_STR_05_0800,
                    "most_recent_date": DATETIME_STR_06_1200,
                    "recent_sample": [
                        {DATETIME_STR_06_1200: "2USERS"},
                        {DATETIME_STR_05_0803: "2USERS"},
                        {DATETIME_STR_05_0800: "2USERS"},
                    ],
                },
                marks=MARK_GEMINI_TEST,
                id="String channel summary",
            ),
        ],
    )
    def test_valid_string_channel_summary(
        self,
        test_app: TestClient,
        login_and_get_token,
        channel_name,
        expected_summary,
    ):
        test_response = test_app.get(
            f"/channels/summary/{channel_name}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        assert test_response.json() == expected_summary

    @pytest.mark.parametrize(
        "channel_name, expected_summary, use_preferred_colourmap",
        [
            pytest.param(
                "FE-204-PSO-P2-CAM-2",
                {
                    "first_date": DATETIME_STR_05_0800,
                    "most_recent_date": DATETIME_STR_06_1200,
                    "recent_sample": [
                        {DATETIME_STR_06_1200: "c63939c6c63139c7"},
                        {DATETIME_STR_05_0803: "c73838c7c738c6c6"},
                        {DATETIME_STR_05_0800: "cc3333ccc333cccc"},
                    ],
                },
                False,
                id="Image channel summary (using system default colourmap)",
            ),
            # repeat the above test but with the user's preferred colour map set to
            # check that the preference overrides the system default colour map
            pytest.param(
                "FE-204-PSO-P2-CAM-2",
                {
                    "first_date": DATETIME_STR_05_0800,
                    "most_recent_date": DATETIME_STR_06_1200,
                    "recent_sample": [
                        {DATETIME_STR_06_1200: "c63939c6c63939c6"},
                        {DATETIME_STR_05_0803: "c73838c6c43ff838"},
                        {DATETIME_STR_05_0800: "cc3333cccc33cccc"},
                    ],
                },
                True,
                id="Image channel summary (using user's preferred colourmap)",
            ),
            pytest.param(
                "FE-204-NSS-WFS",
                {
                    "first_date": DATETIME_STR_05_0803,
                    "most_recent_date": DATETIME_STR_05_0803,
                    "recent_sample": [{DATETIME_STR_05_0803: "93cf6c1833976165"}],
                },
                False,
                id="Float image channel summary (using system default colourmap)",
            ),
            pytest.param(
                "FE-204-NSS-WFS",
                {
                    "first_date": DATETIME_STR_05_0803,
                    "most_recent_date": DATETIME_STR_05_0803,
                    "recent_sample": [{DATETIME_STR_05_0803: "ec3893c79c688f92"}],
                },
                True,
                id="Float image channel summary (using user's preferred colourmap)",
            ),
            pytest.param(
                "FE-204-NSS-WFS-COEF",
                {
                    "first_date": DATETIME_STR_05_0803,
                    "most_recent_date": DATETIME_STR_05_0803,
                    "recent_sample": [{DATETIME_STR_05_0803: "83c0e03ef8c77f30"}],
                },
                False,
                id="Vector channel summary",
            ),
            pytest.param(
                "FE-204-PSO-P1-PD",
                {
                    "first_date": DATETIME_STR_05_0800,
                    "most_recent_date": DATETIME_STR_06_1200,
                    "recent_sample": [
                        {DATETIME_STR_06_1200: "e6e619e419e59859"},
                        {DATETIME_STR_05_0803: "e6e619e419e59859"},
                        {DATETIME_STR_05_0800: "e6e41be41be51a19"},
                    ],
                },
                False,
                id="Waveform channel summary",
            ),
        ],
    )
    def test_valid_thumbnail_channel_summary(
        self,
        test_app: TestClient,
        login_and_get_token,
        channel_name,
        expected_summary,
        use_preferred_colourmap,
    ):
        """
        Compare the response with the expected result, but convert the returned base64
        thumbnails to a perceptual hash beforehand (to prevent bloating this file with
        long base64 strings)
        """

        set_preferred_colourmap(test_app, login_and_get_token, use_preferred_colourmap)
        set_preferred_float_colourmap(
            test_app,
            login_and_get_token,
            use_preferred_colourmap,
        )

        test_response = test_app.get(
            f"/channels/summary/{channel_name}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        json_output = test_response.json()
        for sample in json_output["recent_sample"]:
            for timestamp, checksum in sample.items():
                bytes_thumbnail = base64.b64decode(checksum)
                img = Image.open(io.BytesIO(bytes_thumbnail))
                sample[timestamp] = str(imagehash.phash(img))

        unset_preferred_colourmap(
            test_app,
            login_and_get_token,
            use_preferred_colourmap,
        )
        unset_preferred_float_colourmap(
            test_app,
            login_and_get_token,
            use_preferred_colourmap,
        )

        assert json_output == expected_summary

    @pytest.mark.parametrize(
        "channel_name",
        [
            pytest.param(
                "RANDOM_CHANNEL_NAME",
                id="Channel that doesn't exist",
            ),
            pytest.param(
                1234567,
                id="Integer channel",
            ),
        ],
    )
    def test_invalid_channel_summary(
        self,
        test_app: TestClient,
        login_and_get_token,
        channel_name,
    ):
        test_response = test_app.get(
            f"/channels/summary/{channel_name}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )
        assert test_response.status_code == 400
