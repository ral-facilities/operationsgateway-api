from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest
from starlette.responses import JSONResponse

from operationsgateway_api.src.exceptions import InvalidJWTError

pytestmark = pytest.mark.asyncio


class TestOidcAuth:
    provider_id = "Keycloak"

    @patch("operationsgateway_api.src.auth.oidc.get_username")
    @patch(
        "operationsgateway_api.src.users.user.User.get_user_by_email",
        new_callable=AsyncMock,
    )
    @patch(
        "operationsgateway_api.src.routes.auth.Authentication.create_tokens_response",
    )
    def test_oidc_login_success(
        self,
        mock_create_tokens_response,
        mock_get_user_by_email,
        mock_get_username,
        test_app: TestClient,
    ):
        """Here we are trying to test that a valid ID token yields access
        and refresh tokens."""
        fake_id_token = "does.not.matter"

        # mock the OIDC username extraction (mechanism, username)
        mock_get_username.return_value = ("OIDC", "user@example.ac.uk")

        # mock the user lookup to return a minimal user object
        mock_get_user_by_email.return_value = type(
            "User",
            (),
            {"username": "user", "auth_type": "FedID"},
        )()

        # mock the token response (access body + refresh cookie)
        response_body = {"access": "mock_access_token"}
        mock_response = JSONResponse(content=response_body)
        mock_response.set_cookie(
            key="refresh_token",
            value="mock_refresh_token",
            max_age=604800,
            secure=True,
            httponly=True,
            samesite="Lax",
            path="/refresh",
        )
        mock_create_tokens_response.return_value = mock_response

        # exercise the endpoint
        resp = test_app.post(
            f"/oidc_login/{self.provider_id}",
            headers={"Authorization": f"Bearer {fake_id_token}"},
        )

        # assert success, access token in body and refresh cookie set
        assert resp.status_code == 200
        assert resp.json()["access"] == "mock_access_token"
        assert "refresh_token=" in (resp.headers.get("set-cookie") or "")

    @patch("operationsgateway_api.src.auth.oidc.get_username")
    def test_oidc_login_invalid_jwt_returns_403(
        self,
        mock_get_username,
        test_app: TestClient,
    ):
        """Here we are trying to test that an invalid/malformed ID token
        gives a 403."""
        invalid_token = "not.a.jwt"

        # mock the OIDC layer to raise your domain error
        mock_get_username.side_effect = InvalidJWTError("Invalid OIDC id_token")

        resp = test_app.post(
            f"/oidc_login/{self.provider_id}",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )

        assert resp.status_code == 403
        assert resp.json() == {"detail": "Invalid OIDC id_token"}

    @patch("operationsgateway_api.src.auth.oidc.get_username")
    @patch(
        "operationsgateway_api.src.users.user.User.get_user_by_email",
        new_callable=AsyncMock,
    )
    def test_oidc_login_user_not_found_returns_401(
        self,
        mock_get_user_by_email,
        mock_get_username,
        test_app: TestClient,
    ):
        """Here we are trying to test that a valid token but missing user
        gives a 401."""
        # mock OIDC to return a valid username
        mock_get_username.return_value = ("OIDC", "missing_user@example.com")
        # mock DB lookup to return nothing
        mock_get_user_by_email.return_value = None

        resp = test_app.post(
            f"/oidc_login/{self.provider_id}",
            headers={"Authorization": "Bearer valid_token_but_user_not_found"},
        )

        assert resp.status_code == 401
