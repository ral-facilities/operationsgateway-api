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
        "/users GET",
        "/users/{id_} DELETE",
        "/maintenance POST",
        "/scheduled_maintenance POST",
    ]

    auth_type_list = [
        "local",
        "FedID",
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
    async def get_user_by_email(email: str) -> UserModel:
        """
        Get the document for the user with the specified email from the database
        and populate a UserModel with the details.
        :return: the populated UserModel
        """
        user_data = await MongoDBInterface.find_one(
            "users",
            {"email": email},
        )

        if user_data:
            return UserModel(**user_data)
        else:
            log.error("No user document found for email: '%s'", email)
            raise UnauthorisedError

    @staticmethod
    async def get_all_users():
        """
        Get all user documents from the database.
        :return: a list of user documents
        """
        cursor = MongoDBInterface.find("users", {})
        users = await cursor.to_list(
            length=None,
        )  # Convert the cursor to a list of documents
        return users

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
        """
        updates the routes of the user given by the username
        """
        await MongoDBInterface.update_one(
            "users",
            filter_={"_id": username},
            update={
                "$set": {"authorised_routes": routes},
            },
        )

    @staticmethod
    async def add(login_details):
        """
        adds the user given by the details
        """
        await MongoDBInterface.insert_one(
            "users",
            login_details.model_dump(by_alias=True, exclude_unset=True),
        )

    @staticmethod
    async def delete(username: str):
        """
        deletes the user given by the username
        """
        await MongoDBInterface.delete_one(
            "users",
            filter_={"_id": username},
        )

    @staticmethod
    def check_authorised_routes(authorised_route):
        difference = list(set(authorised_route) - set(User.authorised_route_list))
        return difference

    @staticmethod
    def hash_password(password):
        password_hash = sha256(password.encode()).hexdigest()
        return password_hash

    @staticmethod
    def amend_routes_list(db_routes, routes, add=True):
        if add:
            amended_list = db_routes + list(set(routes) - set(db_routes))
            # This code gets all the routs inside the database and adds it to
            # the routes to be added without causing duplicates
        else:
            amended_list = list(set(db_routes) - set(routes))
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

    @staticmethod
    def check_and_hash(password):
        if password is not None:
            if password == "":
                raise QueryParameterError(
                    "you must have a password with the password field",
                )
            else:
                return User.hash_password(password)

    @staticmethod
    def check_routes(routes):
        if routes is not None:
            invalid_routes = User.check_authorised_routes(routes)
            if invalid_routes:
                log.error("some of the authorised routes entered were invalid")
                raise QueryParameterError(
                    f"some of the routes entered are invalid:  {invalid_routes} ",
                )

    @staticmethod
    async def edit_routes(username, authorised_routes, routes, add=True):
        if routes is not None:
            if authorised_routes is not None:
                routes = User.amend_routes_list(
                    authorised_routes,
                    routes,
                    add,
                )
            await User.update_routes(
                username,
                routes,
            )

    @staticmethod
    def check_password_types(auth_type, password):
        if auth_type == "FedID" and password:
            log.error("no password is required for the auth_type input (FedID)")
            raise QueryParameterError(
                "for the auth_type you put (FedID), no password is required."
                " Please remove this field",
            )

        if auth_type == "local" and password is None:
            log.error("a password is required for the auth_type input (local)")
            raise QueryParameterError(
                "for the auth_type you put (local), a password is required."
                " Please add this field",
            )
