import json

from fastapi.testclient import TestClient
import pytest


class TestGetWaveformByID:
    @pytest.mark.parametrize(
        "record_id, channel_name, expected_first_x, expected_first_y",
        [
            pytest.param(
                "20220407141616",
                "N_COMP_SPEC_TRACE",
                649.8,
                713.0,
                id="Ordinary request",
            ),
        ],
    )
    def test_valid_get_waveform_by_id(
        self,
        test_app: TestClient,
        record_id,
        channel_name,
        expected_first_x,
        expected_first_y,
    ):
        test_response = test_app.get(f"/waveforms/{record_id}/{channel_name}")

        assert test_response.status_code == 200

        assert json.loads(test_response.json()["x"])[0] == expected_first_x
        assert json.loads(test_response.json()["y"])[0] == expected_first_y