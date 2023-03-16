import base64
import hashlib

from fastapi.testclient import TestClient
import pytest


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
        "channel_name, expected_summary",
        [
            pytest.param(
                "N_COMP_FF_IMAGE",
                {
                    "first_date": "2022-04-07T14:16:16",
                    "most_recent_date": "2022-04-08T16:58:57",
                    "recent_sample": [
                        {"2022-04-08T16:58:57": "7eaa7d72354387dcad367bfaa9ca300f"},
                        {"2022-04-08T16:41:36": "ee5f3759eb429ba5abd4ad3e1a9bce16"},
                        {"2022-04-08T16:29:56": "e82a08dbede2ac59f2dfbe427d86a531"},
                    ],
                },
                id="Image channel summary",
            ),
            pytest.param(
                "N_COMP_SPEC_TRACE",
                {
                    "first_date": "2022-04-07T14:16:16",
                    "most_recent_date": "2022-04-08T16:58:57",
                    "recent_sample": [
                        {"2022-04-08T16:58:57": "3f542031460398a672779bca52a619a8"},
                        {"2022-04-08T16:41:36": "e30e17ca5249278431cafdb1a250e73c"},
                        {"2022-04-08T16:29:56": "76b91b973c87b877243d237a84c7d40c"},
                    ],
                },
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
    ):

        """
        Compare the response with the expected result, but convert the returned base64
        thumbnails to an MD5 checksum beforehand (to prevent bloating this file with
        long base64 strings)
        """

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
