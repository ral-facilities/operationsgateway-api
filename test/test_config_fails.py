import re

from pydantic import ValidationError
import pytest

from operationsgateway_api.src.config import (
    APIConfig,
    AuthConfig,
    ExperimentsConfig,
)

BASE_CONFIG = {
    "private_key_path": "/home/user/og-auth/id_rsa",
    "public_key_path": "/home/user/og-auth/id_rsa.pub",
    "jwt_algorithm": "RS256",
    "access_token_validity_mins": 60,
    "refresh_token_validity_days": 7,
    "fedid_server_url": "ldap://fed.cclrc.ac.uk:389",
    "fedid_server_ldap_realm": "FED.CCLRC.AC.UK",
}


class TestConfigFails:
    def test_invalid_timezone(self):
        with pytest.raises(
            SystemExit,
            match="scheduler_background_timezone is not a valid timezone: Mars",
        ):
            ExperimentsConfig.check_timezone(value="Mars")

    def test_user_office_integration_without_api_key_or_url(self):
        # Test that enabling the integration requires the API key and the URL
        with pytest.raises(
            ValidationError,
            match=re.escape(
                "user_office_api_key, user_office_users_service_url must be set "
                "when 'user_office_integration' is enabled",
            ),
        ):
            AuthConfig(**BASE_CONFIG, user_office_integration=True)

    def test_user_office_integration_without_url(self):
        # Test that enabling the integration requires the users service URL
        with pytest.raises(
            ValidationError,
            match=re.escape(
                "user_office_users_service_url must be set when "
                "'user_office_integration' is enabled",
            ),
        ):
            AuthConfig(
                **BASE_CONFIG,
                user_office_integration=True,
                user_office_api_key="an-api-key",
            )

    def test_user_office_integration_without_api_key(self):
        # Test that enabling the integration requires the API key
        with pytest.raises(
            ValidationError,
            match=re.escape(
                "user_office_api_key must be set when "
                "'user_office_integration' is enabled",
            ),
        ):
            AuthConfig(
                **BASE_CONFIG,
                user_office_integration=True,
                user_office_users_service_url="https://example.com",
            )
