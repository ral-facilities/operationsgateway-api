from fastapi.testclient import TestClient

from operationsgateway_api.src.functions import tokens


class TestGetFunctionTokens:
    def test_get_function_tokens(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_response = test_app.get(
            "/functions/tokens",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        assert test_response.json() == tokens
