import socket
from unittest.mock import MagicMock, patch

import ldap
import pytest

from operationsgateway_api.src.auth.authentication import Authentication
from operationsgateway_api.src.exceptions import AuthServerError


class TestFedidEmailLookup:

    # Test successful LDAP lookup returning a valid email address
    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_success(self, mock_ldap_init):
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
        mock_conn.simple_bind_s.assert_called_once()
        mock_conn.search_s.assert_called_once()
        mock_conn.unbind.assert_called_once()

    # Test LDAP lookup where no result is returned for the FedID
    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_no_result(self, mock_ldap_init):
        mock_conn = MagicMock()
        mock_conn.simple_bind_s.return_value = None
        mock_conn.search_s.return_value = []  # No entries
        mock_conn.unbind.return_value = None
        mock_ldap_init.return_value = mock_conn

        result = Authentication.get_email_from_fedid("unknownfedid")
        assert result is None

    # Test LDAP lookup where result is returned but the 'mail' attribute is missing
    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_missing_mail_attr(self, mock_ldap_init):
        mock_conn = MagicMock()
        mock_conn.simple_bind_s.return_value = None
        mock_conn.search_s.return_value = [("dn=whatever", {})]  # No 'mail' key
        mock_conn.unbind.return_value = None
        mock_ldap_init.return_value = mock_conn

        result = Authentication.get_email_from_fedid("userwithoutmail")
        assert result is None

    # Test LDAP lookup where the result has a malformed structure
    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_malformed_entry(self, mock_ldap_init):
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

        result = Authentication.get_email_from_fedid("baduser")
        assert result is None

    # Test the appropriate Errors are returned
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
        with patch(
            "operationsgateway_api.src.auth.authentication.ldap.initialize",
        ) as mock_ldap_init:
            mock_conn = MagicMock()
            mock_conn.simple_bind_s.side_effect = exception_type
            mock_ldap_init.return_value = mock_conn

            with pytest.raises(AuthServerError):
                Authentication.get_email_from_fedid("failinguser")
