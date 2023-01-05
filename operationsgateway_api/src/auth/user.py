import logging

from operationsgateway_api.src.exceptions import UnauthorisedError
from operationsgateway_api.src.models import UserModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface


log = logging.getLogger()


class User:
    @staticmethod
    async def get_user(username: str) -> UserModel:
        """
        Get the document for the user specified from the database and populate a
        UserModel with the detals
        :return: the populated UserModel
        """
        user_data = await MongoDBInterface.find_one(
            "users",
            {"_id": username},
        )

        if user_data:
            return UserModel(**user_data)
        else:
            log.error("No user document found for user: '%s'", username)
            raise UnauthorisedError
