import re

from pydantic import ValidationError
import pytest

from operationsgateway_api.src.config import (
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

    def test_user_office_not_configured(self):
        # Test that the User Office section stays optional.
        # This just checks that the API can be started without it.
        assert AuthConfig(**BASE_CONFIG).user_office is None

    def test_user_office_without_api_key(self):
        # Test that a User Office section is rejected without an API key
        with pytest.raises(
            ValidationError,
            match=re.escape("user_office.api_key"),
        ):
            AuthConfig(
                **BASE_CONFIG,
                user_office={"users_service_url": "https://example.com"},
            )

    def test_user_office_without_users_service_url(self):
        # Test that a User Office section is rejected without a users service URL
        with pytest.raises(
            ValidationError,
            match=re.escape("user_office.users_service_url"),
        ):
            AuthConfig(**BASE_CONFIG, user_office={"api_key": "an-api-key"})
