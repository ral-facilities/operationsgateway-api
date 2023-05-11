import logging

from pydantic import ValidationError

from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.exceptions import (
    ForbiddenError,
    MissingDocumentError,
    ModelError,
)
from operationsgateway_api.src.models import UserSessionModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface

log = logging.getLogger()


class UserSession:
    # TODO - logging
    # TODO - try inheriting this class from UserSession
    def __init__(self, session: UserSessionModel) -> None:
        self.session = session

    @staticmethod
    async def get(id_: str) -> UserSessionModel:
        """
        Given an identifier, retrieve a single user session and return it as a
        `UserSessionModel`
        """

        session_dict = await MongoDBInterface.find_one(
            "sessions",
            filter_={"_id": id_},
        )

        if session_dict:
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

        user_session = await UserSession.get(id_)
        username_match = UserSession._is_user_authorised(
            access_token,
            user_session.username,
        )
        if not username_match:
            raise ForbiddenError(
                "Session attempted to be deleted does not belong to current user",
            )

        delete_result = await MongoDBInterface.delete_one(
            "sessions",
            filter_={"_id": id_},
        )
        log.debug("Number of sessions deleted: %d", delete_result.deleted_count)

    async def upsert(self) -> None:
        """
        Upsert a user session in the database
        """

        update_result = await MongoDBInterface.update_one(
            "sessions",
            {"_id": self.session.id_},
            {"$set": self.session.dict(by_alias=True, exclude_unset=True)},
            upsert=True,
        )

        return True if update_result.upserted_id else False

    @staticmethod
    def _is_user_authorised(access_token: str, session_username: str) -> bool:
        """
        Check if a user's token matches the username for the session. This is used as a
        method of authorisation when deleting sessions
        """

        token_payload = JwtHandler.get_payload(access_token)
        client_userame = token_payload["username"]
        return True if client_userame == session_username else False
