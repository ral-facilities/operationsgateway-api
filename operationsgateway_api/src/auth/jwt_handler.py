from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from typing import Union

from cryptography.hazmat.primitives import serialization
import jwt

from operationsgateway_api.src.auth.auth_keys import get_private_key, get_public_key
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import ForbiddenError
from operationsgateway_api.src.models import UserModel

PRIVATE_KEY = get_private_key()
PUBLIC_KEY = get_public_key()

log = logging.getLogger()
algorithm = Config.config.auth.jwt_algorithm


class JwtHandler:
    blacklisted_tokens_filename = "blacklisted_tokens.txt"

    def __init__(self, user_model: UserModel):
        self.user_model = user_model

    @staticmethod
    def _pack_jwt(payload: dict):
        """
        Packs a given payload into a jwt
        :param payload: the payload to be packed
        :return: The encoded JWT
        """
        bytes_key = bytes(PRIVATE_KEY, encoding="utf8")
        # Load OpenSSH encoded private key
        loaded_private_key = serialization.load_ssh_private_key(
            bytes_key,
            password=None,
        )
        token = jwt.encode(payload, loaded_private_key, algorithm=algorithm)
        return token

    def get_access_token(self):
        """
        Return a signed JWT with selected user details as the payload
        :return: The access JWT
        """
        payload = {}
        payload["username"] = self.user_model.username
        payload["authorised_routes"] = self.user_model.authorised_routes

        if self.user_model.authorised_routes is not None:
            if "/users GET" in self.user_model.authorised_routes:
                payload["userIsAdmin"] = True
        else:
            payload["userIsAdmin"] = False

        payload["exp"] = datetime.now(timezone.utc) + timedelta(
            minutes=Config.config.auth.access_token_validity_mins,
        )
        return self._pack_jwt(payload)

    def get_refresh_token(self):
        """
        Return a signed JWT with to be used as a refresh token
        :return: The refresh JWT
        """
        payload = {}
        payload["exp"] = datetime.now(timezone.utc) + timedelta(
            days=Config.config.auth.refresh_token_validity_days,
        )
        return self._pack_jwt(payload)

    @staticmethod
    def verify_token(token: str):
        """
        Given a JWT, verify that it was signed by the API and that it has not expired
        (checked by default)
        :param token: The JWT to be checked
        :return: a dictionary containing the token's payload
        """
        try:
            return JwtHandler.get_payload(token)
        except Exception as exc:
            message = "Invalid token"
            log.warning(message, exc_info=1)
            raise ForbiddenError(message) from exc

    @staticmethod
    def refresh_token(refresh_token: str, access_token: str):
        """
        Given a JWT refresh token and an access token, verify that the refresh token is
        valid then refresh the access token by updating its expiry time.
        :param refresh_token: The JWT refresh token
        :param access_token: The JWT access token
        :return: The access token JWT with an updated expiry time
        """
        JwtHandler.verify_token(refresh_token)
        # additional check to ensure the token has not been blacklisted
        if refresh_token in JwtHandler.get_blacklisted_tokens():
            message = "Token is blacklisted"
            log.warning(message)
            raise ForbiddenError(message)
        try:
            payload = JwtHandler.get_payload(access_token, {"verify_exp": False})
            payload["exp"] = datetime.now(timezone.utc) + timedelta(
                minutes=Config.config.auth.access_token_validity_mins,
            )
            return JwtHandler._pack_jwt(payload)
        except Exception as exc:
            message = "Unable to refresh token"
            log.warning(message, exc_info=1)
            raise ForbiddenError(message) from exc

    @staticmethod
    def get_blacklisted_tokens():
        """
        JWT refresh tokens (stored in a cookie) can be revoked if necessary in order to
        prevent malicious use of the system. In order to do this the full token string
        must be added to a file "blacklisted_tokens.txt" which must be created at the
        top level of this project (where the config.yml file lives).
        Each token must be on a separate line.
        :return: a list of blacklisted refresh tokens
        """
        try:
            with open(
                Path(__file__).parent.parent.parent
                / JwtHandler.blacklisted_tokens_filename,
                "r",
            ) as f:
                tokens_list = f.read().split("\n")
                return tokens_list
        except FileNotFoundError:
            log.debug(
                "Blacklisted tokens file '%s' not found",
                JwtHandler.blacklisted_tokens_filename,
            )
            return []

    @staticmethod
    def get_payload(access_token: str, options: Union[dict, None] = None) -> dict:
        """
        Get payload from JWT to be used elsewhere in the API
        """
        return jwt.decode(
            access_token,
            PUBLIC_KEY,
            algorithms=[algorithm],
            options=options,
        )
