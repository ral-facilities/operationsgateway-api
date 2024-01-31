import json
from urllib.parse import quote

from fastapi.testclient import TestClient
import pytest


class TestValidateFunction:
    @pytest.mark.parametrize(
        "function, function_types, return_type",
        [
            pytest.param({"name": "a", "expression": "1"}, {}, "scalar", id="Constant"),
            pytest.param(
                {"name": "a", "expression": "a + 1"},
                {"a": "scalar"},
                "scalar",
                id="Function types",
            ),
            pytest.param(
                {"name": "a", "expression": "N_COMP_FF_YPOS / 10"},
                {},
                "scalar",
                id="Scalar operation",
            ),
            pytest.param(
                {"name": "a", "expression": "log(N_COMP_FF_YPOS / 10)"},
                {},
                "scalar",
                id="Scalar element-wise",
            ),
            pytest.param(
                {"name": "a", "expression": "mean(log(N_COMP_FF_YPOS / 10))"},
                {},
                "scalar",
                id="Scalar reductive",
            ),
            pytest.param(
                {"name": "a", "expression": "N_COMP_SPEC_TRACE - 737"},
                {},
                "waveform",
                id="Trace operation",
            ),
            pytest.param(
                {"name": "a", "expression": "log(N_COMP_SPEC_TRACE - 737)"},
                {},
                "waveform",
                id="Trace element-wise",
            ),
            pytest.param(
                {"name": "a", "expression": "mean(log(N_COMP_SPEC_TRACE - 737))"},
                {},
                "scalar",
                id="Trace reductive",
            ),
            pytest.param(
                {"name": "a", "expression": "centre(N_COMP_SPEC_TRACE)"},
                {},
                "scalar",
                id="Trace centre",
            ),
            pytest.param(
                {"name": "a", "expression": "N_COMP_FF_IMAGE - 4"},
                {},
                "image",
                id="Image operation",
            ),
            pytest.param(
                {"name": "a", "expression": "log(N_COMP_FF_IMAGE - 4)"},
                {},
                "image",
                id="Image element-wise",
            ),
            pytest.param(
                {"name": "a", "expression": "mean(log(N_COMP_FF_IMAGE - 4))"},
                {},
                "scalar",
                id="Image reductive",
            ),
        ],
    )
    def test_validate_function(
        self,
        test_app: TestClient,
        login_and_get_token,
        function: dict,
        function_types: dict,
        return_type: str,
    ):
        function_json = quote(json.dumps(function))
        types_json = quote(json.dumps(function_types))
        test_response = test_app.get(
            f"/functions?&function={function_json}&function_types={types_json}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200, test_response.content.decode()[
            "detail"
        ]
        assert test_response.content.decode() == f'"{return_type}"'

    @pytest.mark.parametrize(
        "function, function_types, message",
        [
            pytest.param(
                {"name": "a", "expression": "("},
                {},
                "Unexpected end-of-input in '(', check all brackets are closed",
                id="Left bracket hanging",
            ),
            pytest.param(
                {"name": "a", "expression": ")"},
                {},
                "Unexpected character in ')', check all brackets are opened",
                id="Right bracket hanging",
            ),
            pytest.param(
                {"name": "a", "expression": "a"},
                {},
                "Unexpected variable in 'a': 'a' is not a recognised channel",
                id="Undefined variable",
            ),
            pytest.param(
                {"name": "a", "expression": "centre(1)"},
                {},
                (
                    "Unsupported type in 'centre(1)': "
                    "'centre' accepts ['waveform'] type(s), 'scalar' provided"
                ),
                id="Wrong function argument type",
            ),
            pytest.param(
                {"name": "a", "expression": "unknown(1)"},
                {},
                (
                    "Unsupported function in 'unknown(1)': "
                    "'unknown' is not a recognised function name"
                ),
                id="Unknown function",
            ),
            pytest.param(
                {"name": "a", "expression": "a + b"},
                {"a": "image", "b": "waveform"},
                (
                    "Unsupported type in 'a + b': Operation between types "
                    "['image', 'waveform'] not supported"
                ),
                id="Unsupported operands",
            ),
            pytest.param(
                {"name": "N_COMP_FF_YPOS", "expression": "1"},
                {},
                "Function name 'N_COMP_FF_YPOS' is already a channel name",
                id="Reuse channel name",
            ),
        ],
    )
    def test_validate_function_failure(
        self,
        test_app: TestClient,
        login_and_get_token,
        function: dict,
        function_types: dict,
        message,
    ):
        function_json = quote(json.dumps(function))
        types_json = quote(json.dumps(function_types))
        test_response = test_app.get(
            f"/functions?&function={function_json}&function_types={types_json}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 400
        assert test_response.json()["detail"] == message
