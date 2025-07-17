import jwt
import requests
import logging

from operationsgateway_api.src.config import OidcProviderConfig
from operationsgateway_api.src.exceptions import AuthServerError
from operationsgateway_api.src.config import Config

log = logging.getLogger()


class OidcProvider:
    def __init__(self, provider_config: OidcProviderConfig) -> None:
        self._audience = provider_config.audience
        self._mechanism = provider_config.mechanism
        self._matching_claim = provider_config.matching_claim

        try:
            # Read discovery document
            r = requests.get(provider_config.configuration_url, verify=provider_config.verify_cert)
            r.raise_for_status()
            discovery = r.json()
            self._issuer = discovery["issuer"]
        except Exception as e:
            raise AuthServerError(f"Failed to fetch OIDC discovery: {e}")

        try:
            # Read JWKS keys
            jwks_uri = discovery["jwks_uri"]
            r = requests.get(jwks_uri, verify=provider_config.verify_cert)
            r.raise_for_status()
            jwks_config = r.json()
        except Exception as e:
            raise AuthServerError(f"Failed to fetch JWKS from {jwks_uri}: {e}")

        self._keys = {}
        for key in jwks_config.get("keys", []):
            kid = key.get("kid")
            try:
                self._keys[kid] = jwt.PyJWK(key)
            except jwt.exceptions.PyJWKError as e:
                log.warning(f"Could not load key {kid}: {e}")

    def get_issuer(self) -> str:
        return self._issuer

    def get_key(self, kid: str) -> jwt.PyJWK:
        if kid not in self._keys:
            raise AuthServerError(f"Unknown key ID: {kid}")
        return self._keys[kid]

    def get_audience(self) -> str:
        return self._audience

    def get_mechanism(self) -> str:
        return self._mechanism

    def get_matching_claim(self) -> str:
        return self._matching_claim


class OidcHandler:
    def __init__(self) -> None:
        self._providers = {}

        for name, provider_config in Config.config.auth.oidc_providers.items():
            log.info(f"Loading OIDC provider: {name}")
            try:
                provider = OidcProvider(provider_config)
                self._providers[provider.get_issuer()] = provider
            except Exception as e:
                log.error(f"Failed to initialise OIDC provider '{name}': {e}")
                raise AuthServerError(f"Initialisation error for OIDC provider '{name}'")

    def handle(self, encoded_token: str) -> str:
        try:
            # Decode header/payload to extract issuer and kid
            unverified_header = jwt.get_unverified_header(encoded_token)
            unverified_payload = jwt.decode(encoded_token, options={"verify_signature": False})

            kid = unverified_header["kid"]
            iss = unverified_payload["iss"]
            if iss not in self._providers:
                raise AuthServerError(f"Unknown issuer: {iss}")

            provider = self._providers[iss]
            key = provider.get_key(kid)

            payload = jwt.decode(
                encoded_token,
                key=key,
                algorithms=[key.algorithm_name],
                audience=provider.get_audience(),
                options={
                    "require": ["exp", "aud"],
                    "verify_exp": True,
                    "verify_aud": True,
                },
            )

            matching_claim = payload.get(provider.get_matching_claim())
            if not matching_claim:
                raise AuthServerError("Username claim missing in ID token")

            return matching_claim

        except jwt.exceptions.InvalidTokenError as exc:
            raise AuthServerError("Invalid OIDC ID token") from exc
        except KeyError as e:
            raise AuthServerError(f"Missing required JWT field: {e}")
