from operationsgateway_api.src.mongo.interface import MongoDBInterface


class UserSessionList:
    def __init__(self, username: str) -> None:
        self.username = username

    # TODO - type hint on return once the format has been decided
    async def get_session_list(self):
        """
        Get a list of user sessions that belong to a particular user
        """

        session_list_query = MongoDBInterface.find(
            "sessions",
            filter_={"username": self.username},
            projection="name",
        )

        # TODO - decide what should be included in the list
        results = await MongoDBInterface.query_to_list(session_list_query)
        session_ids = [result["_id"] for result in results]
        return session_ids
