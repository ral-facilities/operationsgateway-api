import socket
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import ldap
import pytest

from operationsgateway_api.src.auth.authentication import Authentication
from operationsgateway_api.src.exceptions import AuthServerError


class TestGetUsers:
    @pytest.mark.asyncio
    async def test_get_users_success(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        # Expected users to validate
        expected_users = [
            {
                "username": "frontend",
                "auth_type": "local",
                "authorised_routes": [],
            },
            {
                "username": "backend",
                "auth_type": "local",
                "authorised_routes": [
                    "/submit/hdf POST",
                    "/submit/manifest POST",
                    "/records/{id_} DELETE",
                    "/experiments POST",
                    "/users POST",
                    "/users PATCH",
                    "/users/{id_} DELETE",
                    "/users GET",
                    "/maintenance PUT",
                    "/scheduled_maintenance PUT",
                ],
            },
        ]

        response = test_app.get(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )
        assert response.status_code == 200

        response_data = response.json()

        # Filter the response to only include `frontend` and `backend` users
        users_to_validate = [
            user
            for user in response_data["users"]
            if user["username"] in {"frontend", "backend"}
        ]

        # Validate the filtered users, we have to be careful
        # because the response from the DB can be in any order
        for user_in_response in users_to_validate:
            matching_user = next(
                (
                    expected_user
                    for expected_user in expected_users
                    if expected_user["username"] == user_in_response["username"]
                ),
                None,
            )

            assert user_in_response["auth_type"] == matching_user["auth_type"]

            # Convert lists to sets for order-independent comparison
            assert set(user_in_response["authorised_routes"]) == set(
                matching_user["authorised_routes"],
            )

    @pytest.mark.asyncio
    async def test_get_users_unauthorised(
        self,
        test_app: TestClient,
        login_as_frontend_and_get_token,
    ):
        response = test_app.get(
            "/users",
            headers={"Authorization": f"Bearer {login_as_frontend_and_get_token}"},
        )
        assert response.status_code == 403

        expected_message = (
            "User 'frontend' is not authorised to use endpoint '/users GET'"
        )
        assert expected_message in response.text

    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_success(self, mock_ldap_init):
        """Test to check a successful LDAP lookup returns a valid email address"""
        mock_conn = MagicMock()
        mock_conn.simple_bind_s.return_value = None
        mock_conn.search_s.return_value = [
            (
                "dn=whatever",
                {"mail": [b"test@example.ac.uk"]},
            ),
        ]
        mock_conn.unbind.return_value = None
        mock_ldap_init.return_value = mock_conn

        result = Authentication.get_email_from_fedid("anyfedid")

        assert result == "test@example.ac.uk"

    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_no_result(self, mock_ldap_init):
        """Test to check a LDAP lookup where no result is returned for the FedID"""
        mock_conn = MagicMock()
        mock_conn.simple_bind_s.return_value = None
        mock_conn.search_s.return_value = []  # No entries
        mock_conn.unbind.return_value = None
        mock_ldap_init.return_value = mock_conn

        result = Authentication.get_email_from_fedid("unknownfedid")
        assert result is None

    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_missing_mail_attr(self, mock_ldap_init):
        """Test to check the case where an LDAP lookup where result is returned
        but the 'mail' attribute is missing"""
        mock_conn = MagicMock()
        mock_conn.simple_bind_s.return_value = None
        mock_conn.search_s.return_value = [("dn=whatever", {})]  # No 'mail' key
        mock_conn.unbind.return_value = None
        mock_ldap_init.return_value = mock_conn

        result = Authentication.get_email_from_fedid("userwithoutmail")
        assert result is None

    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_malformed_entry(self, mock_ldap_init):
        """Test to check an LDAP lookup where the result has a
        malformed/unexpected structure"""
        mock_conn = MagicMock()
        mock_conn.simple_bind_s.return_value = None
        mock_conn.search_s.return_value = [
            (
                "dn=whatever",
                ["not-a-dict"],
            ),
        ]  # Invalid entry type
        mock_conn.unbind.return_value = None
        mock_ldap_init.return_value = mock_conn

        result = Authentication.get_email_from_fedid("wheteverfedid")
        assert result is None

    @pytest.mark.parametrize(
        "exception_type",
        [
            ldap.LDAPError("ldap error"),
            TimeoutError("timeout error"),
            socket.timeout("socket timeout"),
        ],
    )
    def test_get_email_from_fedid_ldap_errors_raise_auth_server_error(
        self,
        exception_type,
    ):
        """Test to check that Authentication.get_email_from_fedid() correctly
        raises an AuthServerError when various LDAP-related errors occur during
        the connection or binding process."""
        with patch(
            "operationsgateway_api.src.auth.authentication.ldap.initialize",
        ) as mock_ldap_init:
            mock_conn = MagicMock()
            mock_conn.simple_bind_s.side_effect = exception_type
            mock_ldap_init.return_value = mock_conn

            with pytest.raises(AuthServerError):
                Authentication.get_email_from_fedid("wheteverfedid")
