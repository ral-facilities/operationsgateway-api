from fastapi.testclient import TestClient
import jwt
import pytest

from operationsgateway_api.src.auth.jwt_handler import PUBLIC_KEY
from operationsgateway_api.src.config import Config


class TestUserIsAdmin:
    @pytest.mark.asyncio
    async def test_user_is_admin(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        # Decode the token to extract the payload
        decoded_payload = jwt.decode(
            login_and_get_token,
            PUBLIC_KEY,
            algorithms=[Config.config.auth.jwt_algorithm],
        )

        assert "userIsAdmin" in decoded_payload

        assert decoded_payload["userIsAdmin"] is True

    @pytest.mark.asyncio
    async def test_user_is_not_admin(
        self,
        test_app: TestClient,
        login_as_frontend_and_get_token,
    ):
        # Decode the token to extract the payload
        decoded_payload = jwt.decode(
            login_as_frontend_and_get_token,
            PUBLIC_KEY,
            algorithms=[Config.config.auth.jwt_algorithm],
        )

        assert "userIsAdmin" in decoded_payload

        assert decoded_payload["userIsAdmin"] is False
