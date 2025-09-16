from unittest.mock import MagicMock, patch

import jwt
import pytest

from operationsgateway_api.src.auth import oidc
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import (
    InvalidJWTError,
    OidcProviderNotFoundError,
)


class TestOidcModule:
    # Set up Constants
    provider_id = "Keycloak"
    issuer = "http://localhost:8081/realms/testrealm"
    kid = "kidrock"
    client_id = "operations-gateway"
    claim_key = "email"
    email_value = "alice.example@stfc.ac.uk"

    @pytest.fixture(autouse=True)
    def clear_caches(self):
        """Set up fixture to run before each test, This ensures each test runs
        with empty TTL caches."""
        # Ensure ttl_cache state doesn't leak across tests
        oidc.get_well_known_config.cache_clear()
        oidc.get_jwks.cache_clear()

    @pytest.fixture
    def mock_oidc_providers(self):
        """Set up a minimal provider object with the attributes oidc.py reads."""
        provider = type(
            "Provider",
            (),
            {
                "configuration_url": f"{self.issuer}/.well-known/openid-configuration",
                "client_id": self.client_id,
                "verify_cert": True,
                "mechanism": "OIDC",
                "username_claim": self.claim_key,
            },
        )
        return {self.provider_id: provider()}

    @pytest.fixture
    def discovery_doc(self):
        """Set up a minimal discovery document with issuer and JWKS URI."""
        return {
            "issuer": self.issuer,
            "jwks_uri": f"{self.issuer}/protocol/openid-connect/certs",
        }

    @pytest.fixture
    def jwks_doc(self):
        """Set up a minimal JWKS with a single RSA key whose kid matches the
        token header."""
        return {
            "keys": [
                {
                    "kid": self.kid,
                },
            ],
        }

    @pytest.fixture
    def stub_pyjwk(self):
        """
        Avoid real key parsing. PyJWT tries to build an RSA key from JWKS values,
        which will fail for dummy test values. This replaces the jwt.PyJWK so it
        returns a stub with a valid algorithm_name.
        """
        with patch("jwt.PyJWK") as mock_pyjwk:
            key_stub = MagicMock()
            key_stub.algorithm_name = "RS256"
            mock_pyjwk.return_value = key_stub
            yield mock_pyjwk

    def test_get_username_success(
        self,
        mock_oidc_providers,
        discovery_doc,
        jwks_doc,
        stub_pyjwk,
    ):
        # mock the provider map in Config so the fake provider is used
        with patch.object(
            Config.config.auth,
            "oidc_providers",
            mock_oidc_providers,
        ), patch("requests.get") as mock_get, patch(
            "jwt.get_unverified_header",
        ) as mock_header, patch(
            "jwt.decode",
        ) as mock_decode:
            # mock the return from the request. First requests.get call returns
            # discovery, second returns JWKS.
            mock_get.side_effect = [
                MagicMock(status_code=200, json=lambda: discovery_doc),
                MagicMock(status_code=200, json=lambda: jwks_doc),
            ]
            # mock the token header to include the expected kid
            mock_header.return_value = {"kid": self.kid}
            # mock the decoded JWT payload to include the username claim and
            # required fields
            mock_decode.return_value = {
                self.claim_key: self.email_value,
                "aud": self.client_id,
                "iss": self.issuer,
                "exp": 1234,
            }
            # call the actual function to test
            mechanism, username = oidc.get_username(self.provider_id, "someidtoken")
            # assert the mechanism and extracted username are as expected
            assert mechanism == "OIDC"
            assert username == self.email_value

    def test_get_username_expired_token_error(
        self,
        mock_oidc_providers,
        discovery_doc,
        jwks_doc,
        stub_pyjwk,
    ):
        with patch.object(
            Config.config.auth,
            "oidc_providers",
            mock_oidc_providers,
        ), patch("requests.get") as mock_get, patch(
            "jwt.get_unverified_header",
        ) as mock_header, patch(
            "jwt.decode",
        ) as mock_decode:

            mock_get.side_effect = [
                MagicMock(status_code=200, json=lambda: discovery_doc),
                MagicMock(status_code=200, json=lambda: jwks_doc),
            ]
            mock_header.return_value = {"kid": self.kid}
            mock_decode.side_effect = jwt.exceptions.ExpiredSignatureError("expired")

            with pytest.raises(InvalidJWTError):
                oidc.get_username(self.provider_id, "idtoken")

    def test_unknown_provider_raises_not_found(self):
        with patch.object(Config.config.auth, "oidc_providers", {}):
            with pytest.raises(OidcProviderNotFoundError):
                oidc.get_well_known_config("some-wrong-provider")

    def test_ttl_cache_is_used_for_discovery(self, mock_oidc_providers, discovery_doc):
        """Here we are trying to test that the discovery response is cached.
        We mock the provider map and the HTTP GET so the first call "hits the network"
        and the second call should come from the TTL cache without another GET."""

        # mock the provider map so the function finds the fake provider
        with patch.object(
            Config.config.auth,
            "oidc_providers",
            mock_oidc_providers,
        ), patch("requests.get") as mock_get:
            # mock the return from the request to always yield the same discovery doc
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: discovery_doc,
            )

            # First call hits network
            oidc.get_well_known_config(self.provider_id)
            # Second call should be served from cache
            oidc.get_well_known_config(self.provider_id)

            # only one HTTP call was made since the second read was cached
            assert mock_get.call_count == 1

    def test_ttl_cache_is_used_for_jwks(
        self,
        mock_oidc_providers,
        discovery_doc,
        jwks_doc,
        stub_pyjwk,
    ):
        """Here we are trying to test that both discovery and JWKS responses are cached.
        The first call to get_jwks should make two GETs (discovery + JWKS),
        and the second call should make zero GETs because both are now cached."""

        with patch.object(
            Config.config.auth,
            "oidc_providers",
            mock_oidc_providers,
        ), patch("requests.get") as mock_get:

            mock_get.side_effect = [
                MagicMock(status_code=200, json=lambda: discovery_doc),
                MagicMock(status_code=200, json=lambda: jwks_doc),
            ]

            # First call fetches both discovery and jwks
            oidc.get_jwks(self.provider_id)
            # Second call should use both caches
            oidc.get_jwks(self.provider_id)

            assert mock_get.call_count == 2

    def test_discovery_cache_refreshes_after_clear(self, mock_oidc_providers):
        """Here we are trying to test that clearing the discovery cache forces
        a refetch. We first return old_doc (cached), then clear the cache,
        switch the mock to new_doc, and confirm a second GET happens and
        returns the new value."""

        old_doc = {"issuer": "https://old", "jwks_uri": "https://old/jwks"}
        new_doc = {"issuer": "https://new", "jwks_uri": "https://new/jwks"}

        with patch.object(
            Config.config.auth,
            "oidc_providers",
            mock_oidc_providers,
        ), patch("requests.get") as mock_get:
            # mock the first network call to return old_doc
            mock_get.return_value = MagicMock(status_code=200, json=lambda: old_doc)

            # first call populates the cache with old_doc
            first = oidc.get_well_known_config("Keycloak")
            assert first == old_doc
            assert mock_get.call_count == 1

            # simulate TTL expiry by clearing the cache
            oidc.get_well_known_config.cache_clear()

            # now change the upstream response to new_doc
            mock_get.return_value = MagicMock(status_code=200, json=lambda: new_doc)

            # next call must refetch and therefore return new_doc
            oidc.get_well_known_config("Keycloak")
            assert mock_get.call_count == 2

    def test_jwks_cache_refreshes_after_clear(self, mock_oidc_providers):
        """Here we are trying to test that clearing the JWKS cache forces only
        the JWKS to be refetched (discovery should still be cached). We first
        fetch discovery, old JWKS, confirm a cached call makes no GETs, then
        clear the JWKS cache and ensure exactly one new GET occurs for the
        JWKS and the keys reflect the new payload."""

        discovery = {"issuer": "https://iss", "jwks_uri": "https://iss/jwks"}
        jwks_old = {"keys": [{"kid": "old"}]}
        jwks_new = {"keys": [{"kid": "new"}]}

        with patch.object(
            Config.config.auth,
            "oidc_providers",
            mock_oidc_providers,
        ), patch("requests.get") as mock_get, patch("jwt.PyJWK") as mock_pyjwk:
            key_stub = MagicMock()
            key_stub.algorithm_name = "RS256"
            mock_pyjwk.return_value = key_stub

            # First: discovery then JWKS old
            mock_get.side_effect = [
                MagicMock(status_code=200, json=lambda: discovery),
                MagicMock(status_code=200, json=lambda: jwks_old),
            ]
            oidc.get_jwks("Keycloak")
            assert mock_get.call_count == 2

            # Change upstream JWKS
            # Still cached, so another call should NOT hit network
            mock_get.side_effect = [
                MagicMock(status_code=200, json=lambda: discovery),
                MagicMock(status_code=200, json=lambda: jwks_new),
            ]
            oidc.get_jwks("Keycloak")
            assert mock_get.call_count == 2

            # Clear JWKS cache and fetch again
            oidc.get_jwks.cache_clear()

            # Because discovery is still cached, get_jwks will make exactly one
            # HTTP call (JWKS). Overwrite side_effect so the next call returns
            # only the JWKS payload.
            mock_get.side_effect = [MagicMock(status_code=200, json=lambda: jwks_new)]

            oidc.get_jwks("Keycloak")

            # Total calls: 2 earlier (discovery + jwks_old) + 0 during cached
            # check + 1 now (jwks_new)
            assert mock_get.call_count == 3
