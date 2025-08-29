from unittest.mock import MagicMock, patch

import pytest
from starlette.responses import JSONResponse

from operationsgateway_api.src.auth.authentication import Authentication
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import AuthServerError, UnauthorisedError


class TestAuthentication:
    def test_fed_server_problem(self, authentication_fed_instance):
        with pytest.raises(Exception):
            authentication_fed_instance.authenticate()

    def test_local_unauthorised(self, authentication_local_instance):
        with pytest.raises(UnauthorisedError):
            authentication_local_instance.authenticate()

    def test_ldap_server_fail(self, monkeypatch, authentication_fed_instance):
        monkeypatch.setattr(
            Config.config.auth,
            "fedid_server_ldap_realm",
            "incorrect_field",
        )
        with pytest.raises((UnauthorisedError, AuthServerError)):
            authentication_fed_instance.authenticate()

    def test_fed_user_success(self, authentication_fed_instance):
        with patch("ldap.initialize") as mock_initialize:
            mock_conn = mock_initialize.return_value
            with patch.object(mock_conn, "simple_bind_s") as mock_simple_bind_s:
                mock_simple_bind_s.return_value = ""
                authentication_fed_instance.authenticate()

    @patch("operationsgateway_api.src.auth.authentication.JwtHandler")
    def test_create_tokens_response(self, mock_jwt_handler_class):

        mock_user_model = MagicMock()
        mock_user_model.username = "fake_user"

        # Mock the JwtHandler instance and return values
        mock_jwt_handler = mock_jwt_handler_class.return_value
        mock_jwt_handler.get_access_token.return_value = {"access": "mock_access_token"}
        mock_jwt_handler.get_refresh_token.return_value = "mock_refresh_token"

        response = Authentication.create_tokens_response(mock_user_model)

        # Assert: response is correct
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert response.body == b'{"access":"mock_access_token"}'

        # Assert: refresh token cookie is correctly set
        set_cookie = response.headers.get("set-cookie", "")
        assert "refresh_token=mock_refresh_token" in set_cookie
        assert "Path=/refresh" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie
        assert "SameSite=Lax" in set_cookie
