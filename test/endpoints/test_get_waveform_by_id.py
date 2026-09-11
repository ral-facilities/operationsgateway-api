import json
from urllib.parse import quote

from fastapi.testclient import TestClient
import pytest

from test.conftest import RECORD_ID_05_0800


class TestGetWaveformByID:
    @pytest.mark.parametrize(
        ["channel_name", "functions", "expected_first_x", "expected_first_y"],
        [
            pytest.param(
                "CM-202-CVC-SP",
                None,
                645.0,
                1356.1113440695408,
                id="Ordinary request",
            ),
            pytest.param(
                "CM-202-CVC-SP",
                {"name": "a", "expression": "CM-202-CVC-SP / 100"},
                645.0,
                1356.1113440695408,
                id="Request with unused function",
            ),
            pytest.param(
                "a",
                {"name": "a", "expression": "CM-202-CVC-SP / 100"},
                645.0,
                13.561113440695408,
                id="Request with used function",
            ),
        ],
    )
    def test_valid_get_waveform_by_id(
        self,
        test_app: TestClient,
        login_and_get_token,
        channel_name,
        functions: "dict[str, str]",
        expected_first_x,
        expected_first_y,
    ):
        if functions is not None:
            functions_str = f"?functions={quote(json.dumps(functions))}"
        else:
            functions_str = ""

        test_response = test_app.get(
            f"/waveforms/{RECORD_ID_05_0800}/{channel_name}{functions_str}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        assert test_response.json()["x"][0] == expected_first_x
        assert test_response.json()["y"][0] == expected_first_y
