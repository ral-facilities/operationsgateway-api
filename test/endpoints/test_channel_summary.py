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
                "SER-202-BI-RH-1",
                {
                    "first_date": "2023-06-04T00:00:00",
                    "most_recent_date": "2023-06-05T23:54:00",
                    "recent_sample": [
                        {"2023-06-05T23:54:00": 45.105075954471815},
                        {"2023-06-05T23:48:00": 42.7879518924901},
                        {"2023-06-05T23:42:00": 40.592569128241514},
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
        "channel_name, expected_summary, use_preferred_colourmap",
        [
            pytest.param(
                "FE-204-PSO-P2-CAM-2",
                {
                    "first_date": "2023-06-05T08:00:00",
                    "most_recent_date": "2023-06-05T16:00:00",
                    "recent_sample": [
                        {"2023-06-05T16:00:00": "fd73e280d830a249bb52bfbfe9bc2b29"},
                        {"2023-06-05T15:00:00": "5e2b10037af476ae852976cbd93b0c22"},
                        {"2023-06-05T14:00:00": "d92faa48f14e40ba308d967501751a6f"},
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
                        {"2022-04-08T16:58:57": "3e78b905df05f4b08a188e0fbd7fcc2a"},
                        {"2022-04-08T16:41:36": "d3e6761e20d18344ade71bd5329b1a36"},
                        {"2022-04-08T16:29:56": "183898d6a41f1b3cb1debdcc8ef0942f"},
                    ],
                },
                True,
                id="Image channel summary (using user's preferred colourmap)",
            ),
            pytest.param(
                "FE-204-PSO-P1-PD",
                {
                    "first_date": "2023-06-05T08:00:00",
                    "most_recent_date": "2023-06-05T16:00:00",
                    "recent_sample": [
                        {"2023-06-05T16:00:00": "0fb865ea1e9a2b21f943c9dfa85b2899"},
                        {"2023-06-05T15:00:00": "b38d616911ede91ad98f7a2605246082"},
                        {"2023-06-05T14:00:00": "8def24d48ac4142ba8975bc018391164"},
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
