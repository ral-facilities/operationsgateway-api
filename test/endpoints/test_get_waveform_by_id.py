import json
from urllib.parse import quote

from fastapi.testclient import TestClient
import pytest


class TestGetWaveformByID:
    @pytest.mark.parametrize(
        "record_id, channel_name, functions, expected_first_x, expected_first_y",
        [
            pytest.param(
                "20230605100000",
                "CM-202-CVC-SP",
                {"name": "a", "expression": "CM-202-CVC-SP / 100"},
                645.0,
                1803.1355895081488,
                id="Ordinary request",
            ),
            pytest.param(
                "20230605100000",
                "a",
                {"name": "a", "expression": "CM-202-CVC-SP / 100"},
                645.0,
                18.031355895081488,
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
        functions: "dict[str, str]",
        expected_first_x,
        expected_first_y,
    ):
        functions_str = quote(json.dumps(functions))
        test_response = test_app.get(
            f"/waveforms/{record_id}/{channel_name}?functions={functions_str}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        assert test_response.json()["x"][0] == expected_first_x
        assert test_response.json()["y"][0] == expected_first_y
