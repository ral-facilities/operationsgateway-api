import json

from fastapi.testclient import TestClient
import pytest


class TestGetWaveformByID:
    @pytest.mark.parametrize(
        "record_id, channel_name, expected_first_x, expected_first_y",
        [
            pytest.param(
                "20230605100000",
                "CM-202-CVC-SP",
                645.0,
                1803.1355895081488,
                id="Ordinary request",
            ),
        ],
    )
    def test_valid_get_waveform_by_id(
        self,
        test_app: TestClient,
        login_and_get_token,
        record_id,
        channel_name,
        expected_first_x,
        expected_first_y,
    ):
        test_response = test_app.get(
            f"/waveforms/{record_id}/{channel_name}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        assert json.loads(test_response.json()["x"])[0] == expected_first_x
        assert json.loads(test_response.json()["y"])[0] == expected_first_y
