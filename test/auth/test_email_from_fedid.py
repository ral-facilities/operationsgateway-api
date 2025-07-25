from unittest.mock import patch, MagicMock
import pytest
import ldap
from operationsgateway_api.src.auth.authentication import Authentication
from operationsgateway_api.src.exceptions import AuthServerError

class TestFedidEmailLookup:

    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_success(self, mock_ldap_init):
        mock_conn = MagicMock()
        mock_conn.simple_bind_s.return_value = None
        mock_conn.search_s.return_value = [
            ("dn=whatever", {"mail": [b"test@example.ac.uk"]})
        ]
        mock_conn.unbind.return_value = None
        mock_ldap_init.return_value = mock_conn

        result = Authentication.get_email_from_fedid("anyfedid")

        assert result == "test@example.ac.uk"
        mock_conn.simple_bind_s.assert_called_once()
        mock_conn.search_s.assert_called_once()
        mock_conn.unbind.assert_called_once()

    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_no_result(self, mock_ldap_init):
        mock_conn = MagicMock()
        mock_conn.simple_bind_s.return_value = None
        mock_conn.search_s.return_value = []  # No entries
        mock_conn.unbind.return_value = None
        mock_ldap_init.return_value = mock_conn

        result = Authentication.get_email_from_fedid("unknownfedid")
        assert result is None

    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_missing_mail_attr(self, mock_ldap_init):
        mock_conn = MagicMock()
        mock_conn.simple_bind_s.return_value = None
        mock_conn.search_s.return_value = [("dn=whatever", {})]  # No 'mail' key
        mock_conn.unbind.return_value = None
        mock_ldap_init.return_value = mock_conn

        result = Authentication.get_email_from_fedid("userwithoutmail")
        assert result is None

    @patch("operationsgateway_api.src.auth.authentication.ldap.initialize")
    def test_get_email_from_fedid_malformed_entry(self, mock_ldap_init):
        mock_conn = MagicMock()
        mock_conn.simple_bind_s.return_value = None
        mock_conn.search_s.return_value = [("dn=whatever", ["not-a-dict"])]  # Invalid entry type
        mock_conn.unbind.return_value = None
        mock_ldap_init.return_value = mock_conn

        result = Authentication.get_email_from_fedid("baduser")
        assert result is None
