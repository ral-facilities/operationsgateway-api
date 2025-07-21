from hashlib import sha256
import logging
from socket import socket

import ldap

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

        ldap.set_option(ldap.OPT_NETWORK_TIMEOUT,5)  # 5 seconds network timeout
        ldap.set_option(ldap.OPT_TIMEOUT, 5) # 5 seconds search timeout

        try:
            conn = ldap.initialize(Config.config.auth.fedid_server_url)
            ldap.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            conn.set_option(ldap.OPT_REFERRALS, 0)

            conn.simple_bind_s()

            base_dn = "dc=fed,dc=cclrc,dc=ac,dc=uk"
            search_filter = f"(cn={fedid})"
            attributes = ["mail"]

            result = conn.search_s(base_dn, ldap.SCOPE_SUBTREE, search_filter,
                                   attributes)
            conn.unbind()

            if result:
                dn, entry = result[0]
                if isinstance(entry, dict):
                    mail_values = entry.get("mail")
                    if mail_values:
                        email = mail_values[0].decode("utf-8")
                        log.debug("Found email '%s' for FedID '%s'", email,
                                  fedid)
                        return email
            else:
                log.info("No email found for FedID '%s'", fedid)
                return None

        except (ldap.LDAPError, TimeoutError, socket.timeout) as e:
            log.warning("LDAP lookup failed or timed out for FedID '%s': %s",
                        fedid, str(e))
            return None
