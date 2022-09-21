from hashlib import sha256
import ldap
import logging

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import (
    AuthServerError, 
    DatabaseError, 
    UnauthorisedError,
)
from operationsgateway_api.src.models import LoginDetails
from operationsgateway_api.src.mongo.interface import MongoDBInterface


log = logging.getLogger()


class Authentication:

    def __init__(self, login_details: LoginDetails):
        self.username = login_details.username
        self.password = login_details.password

    @staticmethod
    async def get_user_document(username: str) -> dict:
        """
        Get the document for the user specified from the database
        :return: a dictionary containing the user's record
        """
        user_document = await MongoDBInterface.find_one(
            "users",
            { "_id": username },
        )
        return user_document

    def authenticate(self, user_document: dict):
        """
        Authenticate the user based on the details found in their database record
        :param user_document: the user's document entry from the database 
        """
        log.debug("user_document: %s", user_document)
        if user_document is None:
            log.warning("Attempted login by user '%s'", self.username)
            raise UnauthorisedError()

        try:
            auth_type = user_document["auth_type"]
        except KeyError:
            message = f"auth_type not set for user '{self.username}'"
            log.error(message)
            raise DatabaseError(msg=message)

        if auth_type == "local":
            self._do_local_auth(user_document)
        elif auth_type == "FedID":
            self._do_fedid_auth()
        else:
            message = (
                f"auth_type '{auth_type}' not recognised for user "
                f"'{self.username}'"
            )
            log.error(message)
            raise DatabaseError(msg=message)

    def _do_local_auth(self, user_document: dict):
        """
        Authenticate a "local" user (functional/non-FedID accounts for control rooms, 
        ingesters etc.)
        :param user_document: the user's document entry from the database 
        """
        log.debug("Doing local auth for '%s'", self.username)
        try: 
            sha256_password = user_document["sha256_password"]
        except KeyError:
            raise DatabaseError(msg=
                f"Encoded password missing in record for user "
                f"'{self.username}'"
            )
        # create a sha256 hash of the provided password and compare it to the 
        # password has that is stored in the database
        sha_256 = sha256()
        sha_256.update(self.password.encode())
        password_hashed = sha_256.hexdigest()
        if password_hashed != sha256_password:
            log.warning("Failed login attempt for user '%s'", self.username)
            raise UnauthorisedError()

    def _do_fedid_auth(self):
        """
        Authenticate a "FedID" user (actual people with entries in the STFC LDAP/Active 
        Directory)
        """
        log.debug("Doing FedID auth for '%s'", self.username)
        try:
            conn = ldap.initialize(Config.config.auth.fedid_server_url)
            ldap.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            ldap.set_option(ldap.OPT_X_TLS_DEMAND, True)
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            ldap.set_option(ldap.OPT_DEBUG_LEVEL, 0)
            conn.start_tls_s()
            conn.simple_bind_s(
                f"{self.username}@{Config.config.auth.fedid_server_ldap_realm}", 
                self.password,
            )
            log.info("Login successful for '%s'", self.username)
            conn.unbind()
        except ldap.INVALID_CREDENTIALS:
            log.info("Invalid username or password for '%s'", self.username)
            conn.unbind()
            raise UnauthorisedError()
        except Exception:
            log.error("Problem with LDAP/AD server", exc_info=1)
            raise AuthServerError()
