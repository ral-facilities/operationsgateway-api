import logging
from typing import Any

from bson.errors import InvalidId
from bson.objectid import ObjectId
from pydantic import ValidationError

from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.exceptions import (
    DatabaseError,
    ForbiddenError,
    MissingDocumentError,
    ModelError,
)
from operationsgateway_api.src.models import UserSessionModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface

log = logging.getLogger()


class UserSession:
    def __init__(self, session: UserSessionModel) -> None:
        self.session = session

    @staticmethod
    async def get(id_: str) -> UserSessionModel:
        """
        Given an identifier, retrieve a single user session and return it as a
        `UserSessionModel`
        """

        try:
            log.info("Finding user session from database: %s", id_)
            session_dict = await MongoDBInterface.find_one(
                "sessions",
                filter_={"_id": ObjectId(id_)},
            )
        except InvalidId as exc:
            raise ModelError("ID provided is not a valid ObjectId") from exc

        if session_dict:
            log.debug(
                "User session found (ID: %s), putting data into UserSessionModel",
                id_,
            )
            try:
                return UserSessionModel(**session_dict)
            except ValidationError as exc:
                raise ModelError(str(exc)) from exc
        else:
            log.error("User session cannot be found. ID: %s", id_)
            raise MissingDocumentError("User session cannot be found")

    @staticmethod
    async def delete(id_: str, access_token: str) -> None:
        """
        Delete a user session given its ID, checking that the session belongs to the
        user who's requesting for the session to be deleted. This should prevent cases
        where a user can delete remove a another user's session
        """

        log.info("Retrieving user session from database before deleting it")
        # Getting user session for the username, to ensure authorisation
        user_session = await UserSession.get(id_)
        username_match = UserSession._is_user_authorised(
            access_token,
            user_session.username,
        )
        log.debug("Is the user authorised to delete this session? %s", username_match)
        if not username_match:
            raise ForbiddenError(
                "Session attempting to be deleted does not belong to current user",
            )

        try:
            delete_result = await MongoDBInterface.delete_one(
                "sessions",
                filter_={"_id": ObjectId(id_)},
            )
        except InvalidId as exc:
            raise ModelError("ID provided is not a valid ObjectId") from exc

        log.debug(
            "Number of sessions deleted: %d. _id: %s",
            delete_result.deleted_count,
            id_,
        )
        if delete_result.deleted_count != 1:
            raise DatabaseError(
                "Unexpected result when deleting. Number of results deleted:"
                f"{delete_result.deleted_count}",
            )

        return delete_result.deleted_count

    async def update(self, access_token: str) -> None:
        """
        Update a user session, checking the session belongs to the user performing the
        update before doing a database transaction
        """

        username_match = UserSession._is_user_authorised(
            access_token,
            self.session.username,
        )
        log.debug("Is the user authorised to update this session? %s", username_match)
        if not username_match:
            raise ForbiddenError(
                "Session attempting to be updated does not belong to current user",
            )

        user_session_update = self.session.dict(
            by_alias=True,
            exclude_unset=True,
            exclude={"id_"},
        )
        try:
            update_result = await MongoDBInterface.update_one(
                "sessions",
                {"_id": ObjectId(self.session.id_)},
                {
                    "$set": user_session_update,
                },
                upsert=False,
            )
        except InvalidId as exc:
            raise ModelError("ID provided is not a valid ObjectId") from exc

        log.debug(
            "Number of sessions matched with id_: %s, number of sessions modified: %s",
            update_result.matched_count,
            update_result.modified_count,
        )
        if update_result.matched_count != 1:
            log.error(
                "User session of ID '%s' couldn't be found in the database."
                " Session: %s",
                self.session.id_,
                user_session_update,
            )
            raise MissingDocumentError("User session cannot be found in the database")
        if update_result.modified_count != 1:
            log.error(
                "Updating session '%s' was unsucessful. Session: %s",
                self.session.id_,
                user_session_update,
            )
            raise DatabaseError(f"Update to {self.session.id_} has been unsuccessful")

    async def insert(self) -> Any:
        """
        Insert a new user session in the database and return the inserted ID
        """

        log.info("Inserting session into database. Session name: %s", self.session.name)
        insert_result = await MongoDBInterface.insert_one(
            "sessions",
            self.session.dict(by_alias=True, exclude_unset=True),
        )
        log.debug("id_ of inserted session: %s", insert_result.inserted_id)
        return insert_result.inserted_id

    @staticmethod
    def _is_user_authorised(access_token: str, session_username: str) -> bool:
        """
        Check if a user's token matches the username for the session. This is used as a
        method of authorisation when deleting sessions
        """

        log.info("Checking if user session belongs to user sending request")
        token_payload = JwtHandler.get_payload(access_token)
        client_userame = token_payload["username"]
        log.debug(
            "Username of session: %s, username inside token: %s",
            session_username,
            client_userame,
        )
        return True if client_userame == session_username else False
