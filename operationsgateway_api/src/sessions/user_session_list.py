import logging

from operationsgateway_api.src.mongo.interface import MongoDBInterface

log = logging.getLogger()


class UserSessionList:
    def __init__(self, username: str) -> None:
        self.username = username

    # TODO - type hint on return once the format has been decided
    async def get_session_list(self):
        """
        Get a list of user sessions that belong to a particular user
        """

        log.info(
            "Finding sessions of user '%s' and querying for the metadata",
            self.username,
        )
        session_list_query = MongoDBInterface.find(
            "sessions",
            filter_={"username": self.username},
            projection=["name", "summary", "timestamp"],
        )

        results = await MongoDBInterface.query_to_list(session_list_query)
        return results
