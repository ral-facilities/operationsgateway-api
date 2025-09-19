from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.config import Config


class TestOidcProviders:

    @pytest.fixture
    def mock_oidc_providers(self):
        return {
            "Keycloak": type(
                "Provider",
                (),
                {
                    "display_name": "Keycloak",
                    "configuration_url": "http://localhost:8081/realms/testrealm"
                    "/.well-known/openid-configuration",
                    "client_id": "operations-gateway",
                    "scope": "openid profile email",
                    "verify_cert": True,
                },
            )(),
            "STFC": type(
                "Provider",
                (),
                {
                    "display_name": "STFC Single Sign On",
                    "configuration_url": "https://example.com/oidc",
                    "client_id": "example-client-id",
                    "scope": "openid",
                    "verify_cert": True,
                },
            )(),
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
                "pkce": True,  # because client_secret is set
                "scope": "openid profile email",
            },
            "STFC": {
                "display_name": "STFC Single Sign On",
                "configuration_url": "https://example.com/oidc",
                "client_id": "example-client-id",
                "pkce": True,  # because client_secret is None
                "scope": "openid",
            },
        }
