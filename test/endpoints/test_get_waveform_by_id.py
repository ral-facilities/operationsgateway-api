import json

from fastapi.testclient import TestClient
import pytest


class TestGetWaveformByID:
    @pytest.mark.parametrize(
        "waveform_id, expected_first_x, expected_first_y",
        [
            pytest.param(
                "62d1637156910a546d0b9a63",
                649.8,
                822.0,
                id="Ordinary request",
            ),
        ],
    )
    def test_valid_get_waveform_by_id(
        self,
        test_app: TestClient,
        waveform_id,
        expected_first_x,
        expected_first_y,
    ):
        test_response = test_app.get(f"/waveforms/{waveform_id}")

        assert test_response.status_code == 200

        assert json.loads(test_response.json()["x"])[0] == expected_first_x
        assert json.loads(test_response.json()["y"])[0] == expected_first_y
