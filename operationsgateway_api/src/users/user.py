from hashlib import sha256
import logging

from operationsgateway_api.src.exceptions import QueryParameterError, UnauthorisedError
from operationsgateway_api.src.models import UserModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface


log = logging.getLogger()


class User:

    authorised_route_list = [
        "/submit/hdf POST",
        "/submit/manifest POST",
        "/records/{id_} DELETE",
        "/experiments POST",
        "/users POST",
        "/users PATCH",
        "/users/{id_} DELETE",
    ]

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

    @staticmethod
    async def update_password(username: str, password: str):
        """
        updates the password of the user given by the username
        """
        await MongoDBInterface.update_one(
            "users",
            filter_={"_id": username},
            update={"$set": {"sha256_password": password}},
        )

    @staticmethod
    async def update_routes(username: str, routes: list):
        await MongoDBInterface.update_one(
            "users",
            filter_={"_id": username},
            update={
                "$set": {"authorised_routes": routes},
            },
        )

    @staticmethod
    def check_authorised_routes(authorised_route):
        difference = list(set(authorised_route) - set(User.authorised_route_list))
        return difference

    @staticmethod
    def hash_password(password):
        password_hash = password = sha256(password.encode()).hexdigest()
        return password_hash

    @staticmethod
    def add_routes_list(db_routes, add_routes):
        amended_list = db_routes + list(set(add_routes) - set(db_routes))
        # This code gets all the routs inside the database and adds it to
        # the routes to be added without causing duplicates

        return amended_list

    @staticmethod
    def remove_routes_list(db_routes, remove_routes):
        amended_list = list(set(db_routes) - set(remove_routes))
        # This code gets all the routs inside the database and removes the routes
        # that are in the remove routes list

        return amended_list

    @staticmethod
    async def check_username_exists(username):
        try:
            if username == "":
                raise ValueError
            user = await User.get_user(username)
        except (UnauthorisedError, ValueError) as err:
            log.error("username field did not exist in the database, _id is required")
            raise QueryParameterError() from err
        return user
