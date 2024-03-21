from unittest.mock import patch

from fastapi.exceptions import HTTPException
import pytest

from operationsgateway_api.src.auth.authorisation import authorise_route


@pytest.fixture
def mock_request():
    class MockRequest:
        def __init__(self, endpoint):
            self.scope = {"endpoint": endpoint}

    return MockRequest(endpoint="/users")


class TestUnauthorisedUser:
    @pytest.mark.parametrize(
        "payload_dict",
        [
            pytest.param({"username": "test_user"}, id="Authorised routes missing"),
            pytest.param(
                {"username": "test_user", "authorised_routes": "test_route"},
                id="Endpoint path missing",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_wrong_value_in_payload(self, mock_request, payload_dict):
        with patch(
            "operationsgateway_api.src.auth.jwt_handler.JwtHandler.verify_token",
            return_value=payload_dict,
        ):
            with patch.dict(
                "operationsgateway_api.src.constants.ROUTE_MAPPINGS",
                {"/users": "value"},
            ):
                credentials_mock = patch(
                    "operationsgateway_api.src.auth.authorisation.mocker.Mock",
                )
                credentials_mock.credentials = ("invalid_access_token",)

                with pytest.raises(
                    HTTPException,
                    match="403: User 'test_user' is not "
                    "authorised to use endpoint 'value'",
                ):
                    await authorise_route(mock_request, credentials_mock)
