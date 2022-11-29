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
                    "recent_sample": [-8582000.0, -8461000.0, -8535000.0],
                },
                id="Scalar channel (number) summary",
            ),
            pytest.param(
                "GEM_SHOT_TYPE_STRING",
                {
                    "first_date": "2022-04-07T14:16:16",
                    "most_recent_date": "2022-04-08T16:58:57",
                    "recent_sample": [
                        "FP",
                        "FP",
                        "FP",
                    ],
                },
                id="Scalar channel (string) summary",
            ),
            # pytest.param(
            #    "N_COMP_FF_IMAGE",
            #    {
            #        "first_date": "2022-04-07T14:16:16",
            #        "most_recent_date": "2022-04-08T16:58:57",
            #        "recent_sample": [],
            #    },
            #    id="Image channel summary",
            # ),
            # pytest.param(
            #    "N_COMP_SPEC_TRACE",
            #    {
            #        "first_date": "2022-04-07T14:16:16",
            #        "most_recent_date": "2022-04-08T16:58:57",
            #        "recent_sample": [],
            #    },
            #    id="Waveform channel summary",
            # ),
        ],
    )
    def test_valid_channel_summary(
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
