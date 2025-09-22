from cachetools.func import ttl_cache
import jwt
import requests

from operationsgateway_api.src.config import Config, OidcProviderConfig
from operationsgateway_api.src.exceptions import (
    AuthServerError,
    InvalidJWTError,
    OidcProviderNotFoundError,
)

# Amount of leeway (in seconds) when validating exp & iat
LEEWAY = 5


@ttl_cache(ttl=24 * 60 * 60)
def get_well_known_config(provider_id: str) -> dict:

    try:
        provider_config: OidcProviderConfig = Config.config.auth.oidc_providers[
            provider_id
        ]
    except KeyError as exc:
        raise OidcProviderNotFoundError from exc

    try:
        r = requests.get(
            provider_config.configuration_url,
            verify=provider_config.verify_cert,
            timeout=5,
        )
    except requests.exceptions.RequestException as exc:
        raise AuthServerError(
            f"Request to {provider_config.configuration_url} failed",
        ) from exc

    return r.json()


@ttl_cache(ttl=2 * 60 * 60)
def get_jwks(provider_id: str) -> dict:

    try:
        provider_config: OidcProviderConfig = Config.config.auth.oidc_providers[
            provider_id
        ]
    except KeyError as exc:
        raise OidcProviderNotFoundError from exc

    well_known_config = get_well_known_config(provider_id)
    jwks_uri = well_known_config["jwks_uri"]

    try:
        r = requests.get(
            jwks_uri,
            verify=provider_config.verify_cert,
            timeout=5,
        )
    except requests.exceptions.RequestException as exc:
        raise AuthServerError(f"Request to {jwks_uri} failed") from exc

    jwks_config = r.json()

    keys = {}
    for key in jwks_config["keys"]:
        kid = key["kid"]
        try:
            keys[kid] = jwt.PyJWK(key)
        except jwt.exceptions.PyJWKError:
            # Possibly unsupported algorithm (e.g. RSA-OAEP)
            pass

    return keys


def get_username(provider_id: str, id_token: str) -> tuple[str, str]:
    try:
        provider_config: OidcProviderConfig = Config.config.auth.oidc_providers[
            provider_id
        ]
    except KeyError as exc:
        raise OidcProviderNotFoundError from exc

    try:
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header["kid"]
        key = get_jwks(provider_id)[kid]

        payload = jwt.decode(
            jwt=id_token,
            key=key,
            algorithms=[key.algorithm_name],
            audience=provider_config.client_id,
            issuer=1,
            verify=True,
            options={
                "require": ["exp", "aud", "iss"],
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
            },
            leeway=LEEWAY,
        )

        return provider_config.mechanism, payload[provider_config.username_claim]

    except jwt.ExpiredSignatureError as exc:
        raise InvalidJWTError("JWT has expired") from exc

    except jwt.exceptions.InvalidTokenError as exc:
        raise InvalidJWTError("Invalid OIDC id_token") from exc
