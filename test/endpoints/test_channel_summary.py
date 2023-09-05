import base64
import hashlib

from fastapi.testclient import TestClient
import pytest

from test.conftest import set_preferred_colourmap, unset_preferred_colourmap


class TestChannelSummary:
    @pytest.mark.parametrize(
        "channel_name, expected_summary",
        [
            pytest.param(
                "N_COMP_FF_E",
                {
                    "first_date": "2022-04-07T14:16:16",
                    "most_recent_date": "2022-04-08T16:58:57",
                    "recent_sample": [
                        {"2022-04-08T16:58:57": -8535000.0},
                        {"2022-04-08T16:41:36": -8461000.0},
                        {"2022-04-08T16:29:56": -8582000.0},
                    ],
                },
                id="Scalar channel (number) summary",
            ),
            pytest.param(
                "GEM_SHOT_TYPE_STRING",
                {
                    "first_date": "2022-04-07T14:16:16",
                    "most_recent_date": "2022-04-08T16:58:57",
                    "recent_sample": [
                        {"2022-04-08T16:58:57": "FP"},
                        {"2022-04-08T16:41:36": "FP"},
                        {"2022-04-08T16:29:56": "FP"},
                    ],
                },
                id="Scalar channel (string) summary",
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
        "channel_name, expected_summary, use_preferred_colourmap",
        [
            pytest.param(
                "N_COMP_FF_IMAGE",
                {
                    "first_date": "2022-04-07T14:16:16",
                    "most_recent_date": "2022-04-08T16:58:57",
                    "recent_sample": [
                        {"2022-04-08T16:58:57": "1c3b60291929cd4b7ddbd8e2d718ee2c"},
                        {"2022-04-08T16:41:36": "015c6decfa5f493005905c223e99fdea"},
                        {"2022-04-08T16:29:56": "9c34c7cecedd1f6e46fe277a027e8ad7"},
                    ],
                },
                False,
                id="Image channel summary (using system default colourmap)",
            ),
            # repeat the above test but with the user's preferred colour map set to
            # check that the preference overrides the system default colour map
            pytest.param(
                "N_COMP_FF_IMAGE",
                {
                    "first_date": "2022-04-07T14:16:16",
                    "most_recent_date": "2022-04-08T16:58:57",
                    "recent_sample": [
                        {"2022-04-08T16:58:57": "6f875d70a1a7eb4c4e8d4fe7da470c4c"},
                        {"2022-04-08T16:41:36": "fc305d83dc57d5c656fd398cdbdcdfb4"},
                        {"2022-04-08T16:29:56": "096f6427fb5030263c8e3e5c9897c809"},
                    ],
                },
                True,
                id="Image channel summary (using user's preferred colourmap)",
            ),
            pytest.param(
                "N_COMP_SPEC_TRACE",
                {
                    "first_date": "2022-04-07T14:16:16",
                    "most_recent_date": "2022-04-08T16:58:57",
                    "recent_sample": [
                        {"2022-04-08T16:58:57": "d3fe6a390d9a10b87cadba980224d4f8"},
                        {"2022-04-08T16:41:36": "4f0be833b33ac301a87a6278305cce13"},
                        {"2022-04-08T16:29:56": "9cf9c60b9c300fc9545b83a52dd72fa6"},
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
        thumbnails to an MD5 checksum beforehand (to prevent bloating this file with
        long base64 strings)
        """

        set_preferred_colourmap(test_app, login_and_get_token, use_preferred_colourmap)

        test_response = test_app.get(
            f"/channels/summary/{channel_name}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        json_output = test_response.json()
        for sample in json_output["recent_sample"]:
            for timestamp, checksum in sample.items():
                bytes_thumbnail = base64.b64decode(checksum)
                sample[timestamp] = hashlib.md5(bytes_thumbnail).hexdigest()

        unset_preferred_colourmap(
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
