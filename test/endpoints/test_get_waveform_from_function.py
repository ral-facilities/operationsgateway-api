import json

from fastapi.testclient import TestClient
import pytest


class TestGetWaveformFromFunction:
    @pytest.mark.parametrize(
        "record_id, function_name, functions, expected_first_x, expected_first_y",
        [
            pytest.param(
                "20230605100000",
                "a",
                {"name": "a", "expression": "CM-202-CVC-SP / 100"},
                645.0,
                18.031355895081488,
                id="Single function",
            ),
        ],
    )
    def test_get_waveform_from_function(
        self,
        test_app: TestClient,
        login_and_get_token,
        record_id: str,
        function_name: str,
        functions: dict,
        expected_first_x: float,
        expected_first_y: float,
    ):
        test_response = test_app.get(
            f"/waveforms/function/{record_id}/{function_name}?&functions={json.dumps(functions)}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        assert test_response.json()["x"][0] == expected_first_x
        assert test_response.json()["y"][0] == expected_first_y
