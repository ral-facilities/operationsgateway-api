import logging

import jwt
import requests

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.config import OidcProviderConfig
from operationsgateway_api.src.exceptions import (
    AuthServerError,
    UnauthorisedError,
    UserError,
)

log = logging.getLogger()


class OidcProvider:
    def __init__(self, provider_config: OidcProviderConfig) -> None:
        self._audience = provider_config.audience
        self._mechanism = provider_config.mechanism
        self._matching_claim = provider_config.matching_claim

        try:
            # Read discovery document
            r = requests.get(
                provider_config.configuration_url,
                verify=provider_config.verify_cert,
            )
            r.raise_for_status()
            discovery = r.json()
            self._issuer = discovery["issuer"]
        except Exception as exc:
            log.exception("Failed to fetch OIDC discovery")
            raise AuthServerError() from exc

        try:
            # Read JWKS keys
            jwks_uri = discovery["jwks_uri"]
            r = requests.get(jwks_uri, verify=provider_config.verify_cert)
            r.raise_for_status()
            jwks_config = r.json()
        except Exception as exc:
            log.exception("Failed to fetch JWKS from %s:", jwks_uri)
            raise AuthServerError() from exc

        self._keys = {}
        for key in jwks_config.get("keys", []):
            kid = key.get("kid")
            if key.get("use") != "sig":
                log.debug("Skipping non-signing key %s (use=%s)", kid, key.get("use"))
                continue
            try:
                self._keys[kid] = jwt.PyJWK(key)
            except (jwt.exceptions.PyJWKError, jwt.exceptions.InvalidKeyError):
                log.warning("Could not load key")

    def get_issuer(self) -> str:
        return self._issuer

    def get_key(self, kid: str) -> jwt.PyJWK:
        if kid not in self._keys:
            log.exception("Unknown key ID %s:", kid)
            raise AuthServerError()
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
            log.info("Loading OIDC provider: %s", name)
            try:
                provider = OidcProvider(provider_config)
                self._providers[provider.get_issuer()] = provider
            except Exception as exc:
                log.error("Initialisation error for OIDC provider %s", name)
                raise AuthServerError() from exc

    def handle(self, encoded_token: str) -> str:
        try:
            # Decode header/payload to extract issuer and kid
            unverified_header = jwt.get_unverified_header(encoded_token)
            unverified_payload = jwt.decode(
                encoded_token,
                options={"verify_signature": False},
            )

            kid = unverified_header["kid"]
            iss = unverified_payload["iss"]
            if iss not in self._providers:
                log.error("Unknown issuer: %s", iss)
                raise AuthServerError()

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

            matching_claim_key = provider.get_matching_claim()
            matching_claim = payload.get(matching_claim_key)
            if not matching_claim:
                log.error("%s claim missing in ID token", matching_claim_key)
                raise UnauthorisedError(
                    f"{matching_claim_key} claim missing in ID token",
                )

            return matching_claim

        except jwt.exceptions.ExpiredSignatureError as exc:
            log.warning("OIDC token has expired")
            raise UnauthorisedError("OIDC token has expired") from exc

        except jwt.exceptions.InvalidTokenError as exc:
            log.error("Invalid OIDC ID token")
            raise UserError("Invalid OIDC ID token") from exc

        except Exception as exc:
            log.exception("Unexpected error during OIDC token handling")
            raise AuthServerError() from exc
