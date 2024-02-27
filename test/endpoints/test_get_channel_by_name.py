from fastapi.testclient import TestClient
import pytest


class TestGetChannelByName:
    @pytest.mark.parametrize(
        "channel_name, expected_metadata",
        [
            pytest.param(
                "SER-202-BI-RH-1",
                {
                    "name": "Relative humidity 202:1",
                    "path": "/Building/Room 202",
                    "type": "scalar",
                    "notation": "normal",
                    "units": "%RH",
                },
                id="Scalar channel",
            ),
            pytest.param(
                "FE-204-PSO-P2-CAM-2",
                {
                    "name": "ps OPCPA pass 2 FF",
                    "path": "/FE-204/PSO/P2",
                    "type": "image",
                },
                id="Image channel",
            ),
            pytest.param(
                "FE-204-PSO-P1-PD",
                {
                    "name": "ps OPCPA pass 1 photodiode trace",
                    "path": "/FE-204/PSO/P1",
                    "type": "waveform",
                },
                id="Waveform channel",
            ),
        ],
    )
    def test_get_channel_by_name(
        self,
        test_app: TestClient,
        login_and_get_token,
        channel_name,
        expected_metadata,
    ):
        test_channel_metadata = test_app.get(
            f"/channels/{channel_name}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_channel_metadata.status_code == 200
        assert test_channel_metadata.json() == expected_metadata
