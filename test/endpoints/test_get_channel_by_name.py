from fastapi.testclient import TestClient
import pytest


class TestGetChannelByName:
    @pytest.mark.parametrize(
        "channel_name, expected_metadata",
        [
            pytest.param(
                "N_COMP_FF_E",
                {
                    "name": "North compressed far field energy",
                    "path": "/LA3/N_COMP/IMAGE",
                    "type": "scalar",
                    "units": "mg",
                    "notation": "scientific",
                    "precision": 4,
                },
                id="Scalar channel",
            ),
            pytest.param(
                "N_COMP_FF_IMAGE",
                {
                    "name": "North compressed far field image",
                    "path": "/LA3/N_COMP/IMAGE",
                    "type": "image",
                },
                id="Image channel",
            ),
            pytest.param(
                "N_COMP_SPEC_TRACE",
                {
                    "name": "North compressed spec waveform",
                    "path": "/LA3/N_COMP/SPEC",
                    "type": "waveform",
                    "x_units": "s",
                    "y_units": "kJ",
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
