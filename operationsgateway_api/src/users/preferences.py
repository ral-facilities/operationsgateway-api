import logging
from typing import Union

from operationsgateway_api.src.exceptions import MissingAttributeError
from operationsgateway_api.src.mongo.interface import MongoDBInterface


log = logging.getLogger()


class UserPreferences:
    @staticmethod
    async def get(username: str, pref_name: str) -> Union[int, float, bool, str]:
        """
        Get the user preference value stored for the given user. If the user doesn't
        have any preferences set yet or doesn't have this particular preference
        set then return a 404 to indicate the value is not set in the database.
        :return: the user preference value
        """
        user_record_with_prefs = await MongoDBInterface.find_one(
            "users",
            {"_id": username},
            projection=[f"user_prefs.{pref_name}"],
        )
        log.debug(
            "User pref_name given to database: %s, Result from database: %s",
            pref_name,
            user_record_with_prefs,
        )

        if "user_prefs" not in user_record_with_prefs:
            raise MissingAttributeError from None
        try:
            pref_value = user_record_with_prefs["user_prefs"][pref_name]
        except KeyError:
            raise MissingAttributeError from None

        log.debug("pref_value: %s", pref_value)
        return pref_value

    @staticmethod
    async def insert(
        username: str,
        pref_name: str,
        value: Union[float, int, bool, str],
    ) -> None:
        """
        Insert a new user preference into the user's record.
        Overwrite any value that already exists for that preference.
        """

        log.debug(
            "Inserting user preference %s of type %s for user %s into database",
            pref_name,
            type(value).__name__,
            username,
        )
        await MongoDBInterface.update_one(
            "users",
            {"_id": username},
            {
                "$set": {f"user_prefs.{pref_name}": value},
            },
        )

    @staticmethod
    async def delete(username: str, pref_name: str) -> None:
        """
        Delete a user preference from the user's record.
        """

        log.debug(
            "Deleting user preference %s for user %s from database",
            pref_name,
            username,
        )
        await MongoDBInterface.update_one(
            "users",
            {"_id": username},
            {
                "$unset": {f"user_prefs.{pref_name}": ""},
            },
        )
