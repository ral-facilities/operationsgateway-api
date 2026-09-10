from unittest.mock import MagicMock, patch

import pytest
import requests
from starlette.responses import JSONResponse

from operationsgateway_api.src.auth.authentication import Authentication
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import AuthServerError, UnauthorisedError
from operationsgateway_api.src.models import LoginDetailsModel


class TestAuthentication:
    def test_fed_server_problem(self, authentication_fed_instance):
        with pytest.raises(Exception):  # noqa: B017
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

    @patch("operationsgateway_api.src.auth.authentication.requests.post")
    def test_user_office_auth_success(self, mock_post):
        # Test that a successful User Office API response is handled correctly.
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {
            "userId": "1116911",
        }

        login_details = LoginDetailsModel(
            username="user@example.com",
            password="password",
        )

        user_id = Authentication.do_user_office_auth(login_details)

        assert user_id == "1116911"
        mock_post.assert_called_once_with(
            "https://api.facilities.rl.ac.uk/users-service/v2/sessions",
            json={
                "username": "user@example.com",
                "password": "password",
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=10,
        )

    @pytest.mark.parametrize(
        "status_code", [401, 403,]
    )  # i can't remember which one it does return so including both
    @patch("operationsgateway_api.src.auth.authentication.requests.post")
    def test_user_office_auth_invalid_credentials(
        self,
        mock_post,
        status_code,
    ):
        # Test that checks a rejected User Office credentials raise UnauthorisedError.
        mock_post.return_value.status_code = status_code

        login_details = LoginDetailsModel(
            username="user@example.com",
            password="incorrect",
        )

        with pytest.raises(UnauthorisedError):
            Authentication.do_user_office_auth(login_details)

    @patch("operationsgateway_api.src.auth.authentication.requests.post")
    def test_user_office_auth_unexpected_response(self, mock_post):
        # Test that an unexpected User Office status raises AuthServerError.
        # Mainly codecov for response.status_code != 201
        mock_post.return_value.status_code = 204
        mock_post.return_value.text = ""

        login_details = LoginDetailsModel(
            username="user@example.com",
            password="password",
        )

        with pytest.raises(AuthServerError):
            Authentication.do_user_office_auth(login_details)

    @patch("operationsgateway_api.src.auth.authentication.requests.post")
    def test_user_office_auth_missing_user_id(self, mock_post):
        # Test that a successful response without userId raises AuthServerError.
        # Incase  we get an empty array which has been seen before
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {}

        login_details = LoginDetailsModel(
            username="user@example.com",
            password="password",
        )

        with pytest.raises(AuthServerError):
            Authentication.do_user_office_auth(login_details)

    # @patch("operationsgateway_api.src.auth.authentication.requests.post")
    # def test_user_office_auth_request_error(self, mock_post):
    #     # Test that a User Office connection failure raises AuthServerError.
    #     mock_post.side_effect = requests.exceptions.RequestException()
    #
    #     login_details = LoginDetailsModel(
    #         username="user@example.com",
    #         password="password",
    #     )
    #
    #     with pytest.raises(AuthServerError):
    #         Authentication.do_user_office_auth(login_details)
    #
    # @patch("operationsgateway_api.src.auth.authentication.requests.post")
    # def test_user_office_auth_invalid_json(self, mock_post):
    #     # Test that invalid JSON from User Office raises AuthServerError.
    #     mock_post.return_value.status_code = 201
    #     mock_post.return_value.json.side_effect = ValueError()
    #
    #     login_details = LoginDetailsModel(
    #         username="user@example.com",
    #         password="password",
    #     )
    #
    #     with pytest.raises(AuthServerError):
    #         Authentication.do_user_office_auth(login_details)

    @patch("operationsgateway_api.src.auth.authentication.requests.get")
    def test_get_user_id_from_user_office_email_success(self, mock_get):
        # Test that an email lookup returns the matching User Office user number.
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "familyName": "Example",
                "givenName": "Test",
                "userNumber": "1116911",
                "email": "user@example.com",
            },
        ]

        user_id = Authentication.get_user_id_from_user_office_email(
            "user@example.com",
        )

        assert user_id == "1116911"
        mock_get.assert_called_once_with(
            (
                "https://api.facilities.rl.ac.uk/"
                "users-service/v2/basic-person-details"
            ),
            params={"emails": "user@example.com"},
            headers={
                "Authorization": (f"Api-key {Config.config.auth.user_office_api_key}"),
                "Accept": "application/json",
            },
            timeout=10,
        )

    # @patch("operationsgateway_api.src.auth.authentication.requests.get")
    # def test_get_user_id_from_user_office_email_not_found(self, mock_get):
    #     # Test that an email with no User Office account returns None.
    #     mock_get.return_value.status_code = 200
    #     mock_get.return_value.json.return_value = []
    #
    #     user_id = Authentication.get_user_id_from_user_office_email(
    #         "missing@example.com",
    #     )
    #
    #     assert user_id is None

    @patch("operationsgateway_api.src.auth.authentication.requests.get")
    def test_get_user_id_from_user_office_email_unexpected_response(
        self,
        mock_get,
    ):
        # Test that an unexpected email lookup status raises AuthServerError.
        mock_get.return_value.status_code = 204
        mock_get.return_value.text = ""

        with pytest.raises(AuthServerError):
            Authentication.get_user_id_from_user_office_email(
                "user@example.com",
            )

    @patch("operationsgateway_api.src.auth.authentication.requests.get")
    def test_get_user_id_from_user_office_email_missing_user_number(
        self,
        mock_get,
    ):
        # Test that a lookup result without userNumber raises AuthServerError.
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "familyName": "Example",
                "email": "user@example.com",
            },
        ]

        with pytest.raises(AuthServerError):
            Authentication.get_user_id_from_user_office_email(
                "user@example.com",
            )

    # @patch("operationsgateway_api.src.auth.authentication.requests.get")
    # def test_get_user_id_from_user_office_email_request_error(
    #     self,
    #     mock_get,
    # ):
    #     # Test that an email lookup connection failure raises AuthServerError.
    #     mock_get.side_effect = requests.exceptions.RequestException()
    #
    #     with pytest.raises(AuthServerError):
    #         Authentication.get_user_id_from_user_office_email(
    #             "user@example.com",
    #         )

    @patch("operationsgateway_api.src.auth.authentication.requests.get")
    def test_get_user_id_from_user_office_email_invalid_json(
        self,
        mock_get,
    ):
        # Test that invalid JSON from an email lookup raises AuthServerError.
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = ValueError()

        with pytest.raises(AuthServerError):
            Authentication.get_user_id_from_user_office_email(
                "user@example.com",
            )

    @patch("operationsgateway_api.src.auth.authentication.requests.post")
    def test_get_user_office_emails(self, mock_post):
        # Test that only requested, active users with emails are returned.
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = [
            {
                "familyName": "Active",
                "userNumber": "13814",
                "email": "active@example.com",
            },
            {
                "familyName": "User [deactivated]",
                "userNumber": "12592",
                "email": "deactivated@example.com",
            },
            {
                "familyName": "No Email",
                "userNumber": "12345",
                "email": None,
            },
            {
                "familyName": "Missing Number",
                "email": "missing-number@example.com",
            },
            {
                "familyName": "Not Requested",
                "userNumber": "99999",
                "email": "not-requested@example.com",
            },
        ]

        emails = Authentication.get_user_office_emails(
            ["13814", "12592", "12345"],
        )

        assert emails == {
            "13814": "active@example.com",
        }

        mock_post.assert_called_once()

        call_args = mock_post.call_args

        assert call_args.args == (
            (
                "https://api.facilities.rl.ac.uk/"
                "users-service/v2/basic-person-details/search"
            ),
        )
        assert call_args.kwargs["params"] == {
            "searchable": "false",
        }
        assert set(call_args.kwargs["json"]["userNumbers"]) == {
            "13814",
            "12592",
            "12345",
        }
        assert call_args.kwargs["headers"] == {
            "Authorization": (f"Api-key {Config.config.auth.user_office_api_key}"),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        assert call_args.kwargs["timeout"] == 10

    # @patch("operationsgateway_api.src.auth.authentication.requests.post")
    # def test_get_user_office_emails_unexpected_response(self, mock_post):
    #     # Test that an unexpected batch lookup status raises AuthServerError.
    #     mock_post.return_value.status_code = 204
    #     mock_post.return_value.text = ""
    #
    #     with pytest.raises(AuthServerError):
    #         Authentication.get_user_office_emails(["13814"])

    # @patch("operationsgateway_api.src.auth.authentication.requests.post")
    # def test_get_user_office_emails_invalid_response_format(self, mock_post):
    #     # Test that a non-list batch lookup response raises AuthServerError.
    #     mock_post.return_value.status_code = 200
    #     mock_post.return_value.json.return_value = {
    #         "userNumber": "13814",
    #         "email": "active@example.com",
    #     }
    #
    #     with pytest.raises(AuthServerError):
    #         Authentication.get_user_office_emails(["13814"])

    @patch("operationsgateway_api.src.auth.authentication.requests.post")
    def test_get_user_office_emails_request_error(self, mock_post):
        # Test that a batch lookup connection failure raises AuthServerError.
        mock_post.side_effect = requests.exceptions.RequestException()

        with pytest.raises(AuthServerError):
            Authentication.get_user_office_emails(["13814"])

    @patch("operationsgateway_api.src.auth.authentication.requests.post")
    def test_get_user_office_emails_invalid_json(self, mock_post):
        # Test that invalid JSON from a batch lookup raises AuthServerError.
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.side_effect = ValueError()

        with pytest.raises(AuthServerError):
            Authentication.get_user_office_emails(["13814"])
