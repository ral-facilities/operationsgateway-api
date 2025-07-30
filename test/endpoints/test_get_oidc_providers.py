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
                    "configuration_url": "http://localhost:8081/realms/"
                    "testrealm/.well-known/openid-configuration",
                    "audience": "operations-gateway",
                },
            )(),
            "AnotherProvider": type(
                "Provider",
                (),
                {
                    "configuration_url": "https://example.com/oidc",
                    "audience": "example-client-id",
                },
            )(),
        }

    def test_list_oidc_providers(self, test_app: TestClient, mock_oidc_providers):
        # Patch the config.auth.oidc_providers dictionary
        with patch.object(Config.config.auth, "oidc_providers", mock_oidc_providers):
            response = test_app.get("/oidc_providers")

        # Assert correct structure and values
        assert response.status_code == 200
        assert response.json() == [
            {
                "display_name": "Keycloak",
                "configuration_url": "http://localhost:8081/realms/"
                "testrealm/.well-known/openid-configuration",
                "client_id": "operations-gateway",
            },
            {
                "display_name": "AnotherProvider",
                "configuration_url": "https://example.com/oidc",
                "client_id": "example-client-id",
            },
        ]
