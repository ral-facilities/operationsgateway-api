from fastapi.testclient import TestClient


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
        assert test_response.json() == [
            {"symbol": "+", "name": "Add"},
            {"symbol": "-", "name": "Subtract"},
            {"symbol": "*", "name": "Multiply"},
            {"symbol": "/", "name": "Divide"},
            {"symbol": "%", "name": "Remainder (modular division)"},
            {"symbol": "^", "name": "Raise to power"},
            {"symbol": "(", "name": "Open bracket"},
            {"symbol": ")", "name": "Close bracket"},
            {
                "symbol": "avg",
                "name": "Mean",
                "details": (
                    "Calculate the mean of a trace (using the y variable) or image input. "
                    "No effect on a scalar input."
                ),
            },
            {
                "symbol": "exp",
                "name": "Exponential",
                "details": (
                    "Raise `e` to the power of the input argument (element-wise if a trace "
                    "or image is provided)."
                ),
            },
            {
                "symbol": "log",
                "name": "Natural logarithm",
                "details": (
                    "Calculate the logarithm in base `e` of the input argument "
                    "(element-wise if a trace or image is provided)."
                ),
            },
            {
                "symbol": "max",
                "name": "Maximum",
                "details": (
                    "Calculate the maximum value in a trace (using the y variable) or "
                    "image input. No effect on a scalar input."
                ),
            },
            {
                "symbol": "min",
                "name": "Minimum",
                "details": (
                    "Calculate the minimum value in a trace (using the y variable) or "
                    "image input. No effect on a scalar input."
                ),
            },
        ]
