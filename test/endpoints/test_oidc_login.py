import base64
import json

from fastapi.testclient import TestClient
import pytest
from httpx import AsyncClient

from operationsgateway_api.src.exceptions import AuthServerError

pytestmark = pytest.mark.asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from operationsgateway_api.src.auth.oidc_handler import OidcHandler
from operationsgateway_api.src.main import app  # or wherever your FastAPI app is

class TestOidcAuth:
    @pytest.fixture
    def override_oidc_handler(self):
        """Override FastAPI dependency to use mock instead of real OidcHandler"""
        mock_handler = AsyncMock()
        mock_handler.handle.return_value = "user@example.ac.uk"
        app.dependency_overrides[OidcHandler] = lambda: mock_handler
        yield
        app.dependency_overrides.clear()

    @patch("operationsgateway_api.src.users.user.User.get_user_by_email",
           new_callable=AsyncMock)
    @patch("operationsgateway_api.src.routes.auth.JwtHandler")
    async def test_oidc_login_success(
            self,
            mock_jwt_handler_class,
            mock_get_user_by_email,override_oidc_handler,
    ):
        from fastapi.testclient import TestClient
        from operationsgateway_api.src.main import app

        fake_id_token = "does.not.matter"

        mock_get_user_by_email.return_value = type("User", (), {
            "username": "user",
            "auth_type": "FedID"
        })()
        mock_jwt_handler = mock_jwt_handler_class.return_value
        mock_jwt_handler.get_access_token.return_value = {
            "access": "mock_access_token"
        }
        mock_jwt_handler.get_refresh_token.return_value = "mock_refresh_token"

        client = TestClient(app)
        response = client.post(
            "/oidc_login",
            headers={"Authorization": f"Bearer {fake_id_token}"},
        )

        assert response.status_code == 200
        assert response.json()["access"] == "mock_access_token"

    def test_oidc_login_invalid_jwt_returns_400(self):
        from fastapi.testclient import TestClient
        from operationsgateway_api.src.main import app

        client = TestClient(app)

        invalid_token = "not.a.jwt"

        response = client.post(
            "/oidc_login",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid OIDC ID token"}

    @patch("operationsgateway_api.src.users.user.User.get_user_by_email",
           new_callable=AsyncMock)
    @patch("operationsgateway_api.src.auth.oidc_handler.OidcHandler.handle",
           new_callable=AsyncMock)
    async def test_oidc_login_user_not_found_returns_401(
            self,
            mock_oidc_handle,
            mock_get_user_by_email,
    ):
        from fastapi.testclient import TestClient
        from operationsgateway_api.src.main import app

        mock_oidc_handle.return_value = "missing_user@example.com"
        mock_get_user_by_email.return_value = None  # Simulate user not in DB

        client = TestClient(app)
        response = client.post(
            "/oidc_login",
            headers={"Authorization": "Bearer valid_token_but_user_not_found"},
        )

        assert response.status_code == 401

