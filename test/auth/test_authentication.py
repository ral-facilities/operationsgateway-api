from unittest.mock import patch

import pytest

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
