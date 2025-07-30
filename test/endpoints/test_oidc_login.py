from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.auth.oidc_handler import OidcHandler
from operationsgateway_api.src.main import app

pytestmark = pytest.mark.asyncio


class TestOidcAuth:
    @pytest.fixture
    def override_oidc_handler(self):
        """Fixture to override the real OidcHandler dependency with a mock."""
        mock_handler = Mock()
        mock_handler.handle.return_value = "user@example.ac.uk"
        app.dependency_overrides[OidcHandler] = lambda: mock_handler
        yield
        app.dependency_overrides.clear()

    @patch(
        "operationsgateway_api.src.users.user.User.get_user_by_email",
        new_callable=AsyncMock,
    )
    @patch("operationsgateway_api.src.routes.auth.JwtHandler")
    def test_oidc_login_success(
        self,
        mock_jwt_handler_class,
        mock_get_user_by_email,
        override_oidc_handler,
        test_app: TestClient,
    ):
        """Test successful OIDC login (Mocks token verification, user lookup,
        and token generation.)"""
        fake_id_token = "does.not.matter"

        mock_get_user_by_email.return_value = type(
            "User",
            (),
            {"username": "user", "auth_type": "FedID"},
        )()
        # Mock JWT handler token generation
        mock_jwt_handler = mock_jwt_handler_class.return_value
        mock_jwt_handler.get_access_token.return_value = {"access": "mock_access_token"}
        mock_jwt_handler.get_refresh_token.return_value = "mock_refresh_token"

        response = test_app.post(
            "/oidc_login",
            headers={"Authorization": f"Bearer {fake_id_token}"},
        )

        assert response.status_code == 200
        assert response.json()["access"] == "mock_access_token"

    def test_oidc_login_invalid_jwt_returns_400(
        self,
        test_app: TestClient,
    ):
        """Test to check the case where the provided JWT is malformed or invalid."""
        invalid_token = "not.a.jwt"

        response = test_app.post(
            "/oidc_login",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid OIDC ID token"}

    @patch(
        "operationsgateway_api.src.auth.oidc_handler.OidcHandler.handle",
        new_callable=Mock,
    )
    @patch(
        "operationsgateway_api.src.users.user.User.get_user_by_email",
        new_callable=AsyncMock,
    )
    async def test_oidc_login_user_not_found_returns_401(
        self,
        mock_user_get,
        mock_oidc_handle,
        test_app: TestClient,
    ):
        """Test to check the case where token is valid but user does not exist in DB"""
        mock_oidc_handle.return_value = "missing_user@example.com"
        mock_user_get.return_value = None  # Simulate user not in DB

        response = test_app.post(
            "/oidc_login",
            headers={"Authorization": "Bearer valid_token_but_user_not_found"},
        )

        assert response.status_code == 401
