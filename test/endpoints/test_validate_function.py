import json

from fastapi.testclient import TestClient
import pytest


class TestValidateFunction:
    @pytest.mark.parametrize(
        "functions, return_types",
        [
            pytest.param([{"name": "a", "expression": "1"}], ["scalar"], id="Constant"),
            pytest.param(
                [
                    {"name": "b", "expression": "1"},
                    {"name": "a", "expression": "b + 1"},
                ],
                ["scalar", "scalar"],
                id="Function types",
            ),
            pytest.param(
                [{"name": "a", "expression": "TS-202-TSM-P1-CAM-2-CENX / 10"}],
                ["scalar"],
                id="Scalar operation",
            ),
            pytest.param(
                [{"name": "a", "expression": "log(TS-202-TSM-P1-CAM-2-CENX / 10)"}],
                ["scalar"],
                id="Scalar element-wise",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "mean(log(TS-202-TSM-P1-CAM-2-CENX / 10))",
                    },
                ],
                ["scalar"],
                id="Scalar reductive",
            ),
            pytest.param(
                [{"name": "a", "expression": "CM-202-CVC-SP - 737"}],
                ["waveform"],
                id="Waveform operation",
            ),
            pytest.param(
                [{"name": "a", "expression": "log(CM-202-CVC-SP - 737)"}],
                ["waveform"],
                id="Waveform element-wise",
            ),
            pytest.param(
                [{"name": "a", "expression": "mean(log(CM-202-CVC-SP - 737))"}],
                ["scalar"],
                id="Waveform reductive",
            ),
            pytest.param(
                [{"name": "a", "expression": "centre(CM-202-CVC-SP)"}],
                ["scalar"],
                id="Waveform centre",
            ),
            pytest.param(
                [{"name": "a", "expression": "FE-204-NSO-P1-CAM-1 - 4"}],
                ["image"],
                id="Image operation",
            ),
            pytest.param(
                [{"name": "a", "expression": "log(FE-204-NSO-P1-CAM-1 - 4)"}],
                ["image"],
                id="Image element-wise",
            ),
            pytest.param(
                [{"name": "a", "expression": "mean(log(FE-204-NSO-P1-CAM-1 - 4))"}],
                ["scalar"],
                id="Image reductive",
            ),
        ],
    )
    def test_validate_function_success(
        self,
        test_app: TestClient,
        login_and_get_token,
        functions: "list[dict[str, str]]",
        return_types: "list[str]",
    ):
        test_response = test_app.post(
            "/functions/validate",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            content=json.dumps(functions),
        )

        assert test_response.status_code == 200, test_response.content.decode()
        assert json.loads(test_response.content.decode()) == return_types

    @pytest.mark.parametrize(
        "functions, message",
        [
            pytest.param(
                [{"name": "a", "expression": "("}],
                (
                    "Error at index 0: expression '(' has unexpected end-of-input, "
                    "check all brackets are closed"
                ),
                id="Left bracket hanging",
            ),
            pytest.param(
                [{"name": "a", "expression": ")"}],
                (
                    "Error at index 0: expression ')' has unexpected character, "
                    "check all brackets are opened"
                ),
                id="Right bracket hanging",
            ),
            pytest.param(
                [{"name": "a", "expression": "a"}],
                "Error at index 0: 'a' is not a recognised channel",
                id="Undefined variable",
            ),
            pytest.param(
                [{"name": "a", "expression": "centre(1)"}],
                (
                    "Error at index 0: 'centre' accepts {'waveform'} type(s), 'scalar' "
                    "provided"
                ),
                id="Wrong function argument type",
            ),
            pytest.param(
                [{"name": "a", "expression": "unknown(1)"}],
                "Error at index 0: 'unknown' is not a recognised builtin function name",
                id="Unknown function",
            ),
            pytest.param(
                [
                    {
                        "name": "b",
                        "expression": "FE-204-NSO-P1-CAM-1",
                    },
                    {
                        "name": "c",
                        "expression": "CM-202-CVC-SP",
                    },
                    {"name": "a", "expression": "b + c"},
                ],
                (
                    "Error at index 2: Operation between types [<ChannelDtype.IMAGE: "
                    "'image'>, <ChannelDtype.WAVEFORM: 'waveform'>] not supported"
                ),
                id="Unsupported operands",
            ),
            pytest.param(
                [{"name": "TS-202-TSM-P1-CAM-2-CENX", "expression": "1"}],
                (
                    "Error at index 0: name 'TS-202-TSM-P1-CAM-2-CENX' is already a "
                    "channel name"
                ),
                id="Reuse channel name",
            ),
            pytest.param(
                [{"name": "a", "expression": "1"}, {"name": "a", "expression": "2"}],
                "Error at index 1: name 'a' is already a function name",
                id="Reuse function name",
            ),
            pytest.param(
                [{"name": "mean", "expression": "1"}],
                "Error at index 0: name 'mean' is already a builtin name",
                id="Reuse builtin name",
            ),
            pytest.param(
                [{"name": "b@d_n@m3", "expression": "1"}],
                (
                    "Error at index 0: name 'b@d_n@m3' must start with a letter, and "
                    "can only contain letters, digits, '-' or '_' characters"
                ),
                id="Bad name",
            ),
            pytest.param(
                [{"name": "bad + name", "expression": "1"}],
                (
                    "Error at index 0: name 'bad + name' must start with a letter, and "
                    "can only contain letters, digits, '-' or '_' characters"
                ),
                id="Name with spaces",
            ),
            pytest.param(
                [{"name": "1", "expression": "1"}],
                (
                    "Error at index 0: name '1' must start with a letter, and can only "
                    "contain letters, digits, '-' or '_' characters"
                ),
                id="Name without letters",
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
        test_response = test_app.post(
            "/functions/validate",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            content=json.dumps(functions),
        )

        assert test_response.status_code == 400, test_response.content.decode()
        assert test_response.json()["detail"] == message

    def test_validate_function_empty(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_response = test_app.post(
            "/functions/validate",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            content=json.dumps([{"name": "", "expression": ""}]),
        )

        assert test_response.status_code == 422, test_response.content.decode()
        assert len(test_response.json()["detail"]) == 2
        for detail in test_response.json()["detail"]:
            assert detail["msg"] == "String should have at least 1 character"
