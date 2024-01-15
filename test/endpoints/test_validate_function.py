from fastapi.testclient import TestClient
import pytest


class TestValidateFunction:
    @pytest.mark.parametrize("expression", [pytest.param("1")])
    def test_validate_function(
        self,
        test_app: TestClient,
        login_and_get_token,
        expression,
    ):
        test_response = test_app.get(
            f"/functions?&expression={expression}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

    @pytest.mark.parametrize(
        "expression, message",
        [pytest.param("(", "ERR005 - Mismatched brackets: ')'Token Error")],
    )
    def test_validate_function_failure(
        self,
        test_app: TestClient,
        login_and_get_token,
        expression,
        message,
    ):
        test_response = test_app.get(
            f"/functions?&expression={expression}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 400

        expected_message = f"Error evaluating expression '{expression}': {message}"
        assert test_response.json()["detail"] == expected_message
