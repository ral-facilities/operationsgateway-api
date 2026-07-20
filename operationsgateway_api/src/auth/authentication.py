from hashlib import sha256
import logging
import socket

import ldap
import requests
from starlette.responses import JSONResponse

from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import (
    AuthServerError,
    DatabaseError,
    UnauthorisedError,
)
from operationsgateway_api.src.models import LoginDetailsModel, UserModel

log = logging.getLogger()


class Authentication:
    def __init__(self, login_details: LoginDetailsModel, user_model: UserModel):
        self.login_details = login_details
        self.user_model = user_model

    def authenticate(self):
        """
        Authenticate the user based on the details found in their database record
        """
        auth_type = self.user_model.auth_type
        if auth_type == "local":
            self._do_local_auth()
        elif auth_type == "FedID":
            self._do_fedid_auth()
        else:
            message = (
                f"auth_type '{auth_type}' not recognised for user "
                f"'{self.login_details.username}'"
            )
            log.error(message)
            raise DatabaseError(msg=message)

    def _do_local_auth(self):
        """
        Authenticate a "local" user (functional/non-FedID accounts for control rooms,
        ingesters etc.)
        :param user_document: the user's document entry from the database
        """
        username = self.login_details.username
        log.debug("Doing local auth for '%s'", username)
        if self.user_model.sha256_password is None:
            raise DatabaseError(
                msg=f"Encoded password missing in record for user '{username}'",
            )
        # create a sha256 hash of the provided password and compare it to the
        # password has that is stored in the database
        sha_256 = sha256()
        sha_256.update(self.login_details.password.encode())
        password_hashed = sha_256.hexdigest()
        if password_hashed != self.user_model.sha256_password:
            log.warning("Failed login attempt for user '%s'", username)
            raise UnauthorisedError()

    def _do_fedid_auth(self):
        """
        Authenticate a "FedID" user (actual people with entries in the STFC LDAP/Active
        Directory)
        """
        username = self.login_details.username
        log.debug("Doing FedID auth for '%s'", username)
        try:
            conn = ldap.initialize(Config.config.auth.fedid_server_url)
            ldap.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            ldap.set_option(ldap.OPT_X_TLS_DEMAND, True)
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            ldap.set_option(ldap.OPT_DEBUG_LEVEL, 0)
            conn.start_tls_s()
            conn.simple_bind_s(
                f"{username}@{Config.config.auth.fedid_server_ldap_realm}",
                self.login_details.password,
            )
            log.info("Login successful for '%s'", username)
            conn.unbind()
        except ldap.INVALID_CREDENTIALS as exc:
            log.info("Invalid username or password for '%s'", username)
            conn.unbind()
            raise UnauthorisedError() from exc
        except Exception as exc:
            log.exception("Problem with LDAP/AD server")
            raise AuthServerError() from exc

    @staticmethod
    def get_email_from_fedid(fedid: str) -> str | None:
        """
        Look up a user's email address from LDAP using their FedID.
        """
        log.debug("Looking up email for FedID: %s", fedid)

        ldap.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)  # 5 seconds network timeout
        ldap.set_option(ldap.OPT_TIMEOUT, 5)  # 5 seconds search timeout

        try:
            conn = ldap.initialize(Config.config.auth.fedid_server_url)
            ldap.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            conn.set_option(ldap.OPT_REFERRALS, 0)

            conn.simple_bind_s()

            base_dn = "dc=fed,dc=cclrc,dc=ac,dc=uk"
            search_filter = f"(cn={fedid})"
            attributes = ["mail"]

            result = conn.search_s(
                base_dn,
                ldap.SCOPE_SUBTREE,
                search_filter,
                attributes,
            )
            conn.unbind()

            if result:
                dn, entry = result[0]
                if isinstance(entry, dict):
                    mail_values = entry.get("mail")
                    if mail_values:
                        email = mail_values[0].decode("utf-8")
                        log.debug("Found email '%s' for FedID '%s'", email, fedid)
                        return email

            log.info("No email found for FedID '%s'", fedid)
            return None

        except (ldap.LDAPError, TimeoutError, socket.timeout) as exc:
            log.warning("LDAP lookup failed or timed out for FedID '%s'", fedid)
            raise AuthServerError() from exc

    @staticmethod
    def create_tokens_response(user_model):

        # Create access/refresh tokens
        jwt_handler = JwtHandler(user_model)
        access_token = jwt_handler.get_access_token()
        refresh_token = jwt_handler.get_refresh_token()

        # Create response with access token and refresh token cookie
        response = JSONResponse(content=access_token)
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=604800,  # 7 days
            secure=True,
            httponly=True,
            samesite="Lax",
            path="/refresh",
        )

        log.info(
            "Refresh token created '%s':",
            refresh_token,
        )

        return response

    @staticmethod
    def do_user_office_auth(login_details: LoginDetailsModel) -> str:
        """
        Authenticate a User Office user.
        User enters email + password.
        User Office returns userId
        The returned userId is used to find the user in Mongo.
        """
        username = login_details.username
        password = login_details.password

        log.debug("Doing User Office auth for '%s'", username)

        login_url = "https://api.facilities.rl.ac.uk/users-service/v2/sessions"

        try:
            response = requests.post(
                login_url,
                json={
                    "username": username,
                    "password": password,
                },
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )

            if response.status_code in (401, 403):
                log.info("Invalid User Office username or password for '%s'", username)
                raise UnauthorisedError()

            if response.status_code != 201:
                log.error(
                    "Unexpected User Office auth response for '%s': %s %s",
                    username,
                    response.status_code,
                    response.text,
                )
                response.raise_for_status()
                raise AuthServerError()

            login_response = response.json()
            user_id = login_response.get("userId")

            if not user_id:
                log.error("User Office auth response did not contain userId")
                raise AuthServerError()

            log.info(
                "User Office login successful for '%s', userId '%s'",
                username,
                user_id,
            )

            return user_id

        except UnauthorisedError:
            raise
        except requests.exceptions.RequestException as exc:
            log.exception("Problem with User Office auth service")
            raise AuthServerError() from exc
        except ValueError as exc:
            log.exception("Invalid JSON response from User Office auth service")
            raise AuthServerError() from exc

    @staticmethod
    def get_user_id_from_user_office_email(email: str) -> str | None:
        """
        Look up a User Office user by email address.

        Returns the User Office userId if found, otherwise None.
        """
        log.debug("Looking up User Office user '%s'", email)

        lookup_url = (
            "https://api.facilities.rl.ac.uk/users-service/v2/basic-person-details"
        )

        try:
            response = requests.get(
                lookup_url,
                params={"emails": email},
                headers={
                    "Authorization": (
                        f"Api-key {Config.config.auth.user_office_api_key}"
                    ),
                    "Accept": "application/json",
                },
                timeout=10,
            )

            if response.status_code != 200:
                log.error(
                    "Unexpected User Office lookup response for '%s': %s %s",
                    email,
                    response.status_code,
                    response.text,
                )
                response.raise_for_status()
                raise AuthServerError()

            lookup_response = response.json()

            if not lookup_response:
                log.info("No User Office account found for '%s'", email)
                return None

            user_id = lookup_response[0].get("userNumber")

            if not user_id:
                log.error(
                    "User Office lookup response did not contain userNumber"
                )
                raise AuthServerError()

            log.info(
                "User Office lookup successful for '%s', userId '%s'",
                email,
                user_id,
            )

            return str(user_id)

        except requests.exceptions.RequestException as exc:
            log.exception("Problem with User Office lookup service")
            raise AuthServerError() from exc
        except ValueError as exc:
            log.exception("Invalid JSON response from User Office lookup service")
            raise AuthServerError() from exc

    @staticmethod
    def get_user_office_emails(
            user_numbers: list[str],
    ) -> dict[str, str | None]:
        """
        Look up multiple User Office users in one request.

        Returns a mapping of user number to email address.
        """
        lookup_url = (
            "https://api.facilities.rl.ac.uk/"
            "users-service/v2/basic-person-details"
        )

        log.debug(
            "Looking up %d User Office users",
            len(user_numbers),
        )

        try:
            response = requests.get(
                lookup_url,
                params=[
                    ("userNumbers", user_number)
                    for user_number in user_numbers
                ],
                headers={
                    "Authorization": (
                        f"Api-key {Config.config.auth.user_office_api_key}"
                    ),
                    "Accept": "application/json",
                },
                timeout=10,
            )

            if response.status_code != 200:
                log.error(
                    "Unexpected User Office lookup response: %s %s",
                    response.status_code,
                    response.text,
                )
                response.raise_for_status()
                raise AuthServerError()

            lookup_response = response.json()

            if not isinstance(lookup_response, list):
                log.error("Unexpected User Office lookup response format")
                raise AuthServerError()

            requested_numbers = {str(number) for number in user_numbers}

            emails = {
                str(person["userNumber"]): person.get("email")
                for person in lookup_response
                if person.get("userNumber") is not None
                   and str(person["userNumber"]) in requested_numbers
            }

            # Include users not returned by User Office with a None email.
            return {
                user_number: emails.get(user_number)
                for user_number in requested_numbers
            }

        except requests.exceptions.RequestException as exc:
            log.exception("Problem with User Office lookup service")
            raise AuthServerError() from exc
        except ValueError as exc:
            log.exception(
                "Invalid JSON response from User Office lookup service")
            raise AuthServerError() from exc