from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.config import Config, OidcProviderConfig


class TestOidcProviders:

    @pytest.fixture
    def mock_oidc_providers(self):
        return {
            "Keycloak": OidcProviderConfig(
                display_name="Keycloak",
                configuration_url="http://localhost:8081/realms/testrealm/.well-known/openid-configuration",
                client_id="operations-gateway",
                verify_cert=True,
                mechanism="oidc",
                username_claim="email",
            ),
            "STFC": OidcProviderConfig(
                display_name="STFC Single Sign On",
                configuration_url="https://example.com/oidc",
                client_id="example-client-id",
                verify_cert=True,
                mechanism="oidc",
                username_claim="email",
            ),
        }

    def test_list_oidc_providers(self, test_app: TestClient, mock_oidc_providers):
        with patch.object(Config.config.auth, "oidc_providers", mock_oidc_providers):
            resp = test_app.get("/oidc_providers")

        assert resp.status_code == 200
        assert resp.json() == {
            "Keycloak": {
                "display_name": "Keycloak",
                "configuration_url": "http://localhost:8081/realms/testrealm/"
                ".well-known/openid-configuration",
                "client_id": "operations-gateway",
                "pkce": True,
                "scope": "openid email",
            },
            "STFC": {
                "display_name": "STFC Single Sign On",
                "configuration_url": "https://example.com/oidc",
                "client_id": "example-client-id",
                "pkce": True,
                "scope": "openid email",
            },
        }
