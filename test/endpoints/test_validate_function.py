import json
from urllib.parse import quote

from fastapi.testclient import TestClient
import pytest


class TestValidateFunction:
    @pytest.mark.parametrize(
        "functions, return_type",
        [
            pytest.param([{"name": "a", "expression": "1"}], "scalar", id="Constant"),
            pytest.param(
                [
                    {"name": "a", "expression": "b + 1"},
                    {"name": "b", "expression": "1", "return_type": "scalar"},
                ],
                "scalar",
                id="Function types",
            ),
            pytest.param(
                [{"name": "a", "expression": "TS-202-TSM-P1-CAM-2-CENX / 10"}],
                "scalar",
                id="Scalar operation",
            ),
            pytest.param(
                [{"name": "a", "expression": "log(TS-202-TSM-P1-CAM-2-CENX / 10)"}],
                "scalar",
                id="Scalar element-wise",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "mean(log(TS-202-TSM-P1-CAM-2-CENX / 10))",
                    },
                ],
                "scalar",
                id="Scalar reductive",
            ),
            pytest.param(
                [{"name": "a", "expression": "CM-202-CVC-SP - 737"}],
                "waveform",
                id="Trace operation",
            ),
            pytest.param(
                [{"name": "a", "expression": "log(CM-202-CVC-SP - 737)"}],
                "waveform",
                id="Trace element-wise",
            ),
            pytest.param(
                [{"name": "a", "expression": "mean(log(CM-202-CVC-SP - 737))"}],
                "scalar",
                id="Trace reductive",
            ),
            pytest.param(
                [{"name": "a", "expression": "centre(CM-202-CVC-SP)"}],
                "scalar",
                id="Trace centre",
            ),
            pytest.param(
                [{"name": "a", "expression": "FE-204-NSO-P1-CAM-1 - 4"}],
                "image",
                id="Image operation",
            ),
            pytest.param(
                [{"name": "a", "expression": "log(FE-204-NSO-P1-CAM-1 - 4)"}],
                "image",
                id="Image element-wise",
            ),
            pytest.param(
                [{"name": "a", "expression": "mean(log(FE-204-NSO-P1-CAM-1 - 4))"}],
                "scalar",
                id="Image reductive",
            ),
        ],
    )
    def test_validate_function(
        self,
        test_app: TestClient,
        login_and_get_token,
        functions: "list[dict[str, str]]",
        return_type: str,
    ):
        url = "/functions/validate/a?"
        for function_dict in functions:
            url += f"&functions={quote(json.dumps(function_dict))}"

        test_response = test_app.get(
            url,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200, test_response.content.decode()
        assert test_response.content.decode() == f'"{return_type}"'

    @pytest.mark.parametrize(
        "functions, message",
        [
            pytest.param(
                [{"name": "a", "expression": "("}],
                "Unexpected end-of-input in '(', check all brackets are closed",
                id="Left bracket hanging",
            ),
            pytest.param(
                [{"name": "a", "expression": ")"}],
                "Unexpected character in ')', check all brackets are opened",
                id="Right bracket hanging",
            ),
            pytest.param(
                [{"name": "a", "expression": "a"}],
                "Unexpected variable in 'a': 'a' is not a recognised channel",
                id="Undefined variable",
            ),
            pytest.param(
                [{"name": "a", "expression": "centre(1)"}],
                (
                    "Unsupported type in 'centre(1)': "
                    "'centre' accepts {'waveform'} type(s), 'scalar' provided"
                ),
                id="Wrong function argument type",
            ),
            pytest.param(
                [{"name": "a", "expression": "unknown(1)"}],
                (
                    "Unsupported function in 'unknown(1)': "
                    "'unknown' is not a recognised builtin function name"
                ),
                id="Unknown function",
            ),
            pytest.param(
                [
                    {"name": "c", "expression": "a + b"},
                    {
                        "name": "a",
                        "expression": "FE-204-NSO-P1-CAM-1",
                        "return_type": "image",
                    },
                    {
                        "name": "b",
                        "expression": "CM-202-CVC-SP",
                        "return_type": "waveform",
                    },
                ],
                (
                    "Unsupported type in 'a + b': Operation between types "
                    "['image', 'waveform'] not supported"
                ),
                id="Unsupported operands",
            ),
            pytest.param(
                [{"name": "TS-202-TSM-P1-CAM-2-CENX", "expression": "1"}],
                "Function name 'TS-202-TSM-P1-CAM-2-CENX' is already a channel name",
                id="Reuse channel name",
            ),
        ],
    )
    def test_validate_function_failure(
        self,
        test_app: TestClient,
        login_and_get_token,
        functions: "list[dict]",
        message,
    ):
        url = f"/functions/validate/{functions[0]['name']}?"
        for function_dict in functions:
            url += f"&functions={quote(json.dumps(function_dict))}"

        test_response = test_app.get(
            url,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 400
        assert test_response.json()["detail"] == message
