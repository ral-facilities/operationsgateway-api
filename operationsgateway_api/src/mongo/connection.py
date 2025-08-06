import asyncio
from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from operationsgateway_api.src.config import Config


class MongoDBConnection:
    """
    Class to store database connections, the database and collection
    """

    def __init__(self) -> None:
        mongodb_config = Config.config.mongodb
        self.mongo_client = AsyncIOMotorClient(
            mongodb_config.mongodb_url.get_secret_value(),
        )
        self.mongo_client.get_io_loop = asyncio.get_event_loop
        self.db: AsyncIOMotorDatabase = self.mongo_client[mongodb_config.database_name]


@lru_cache
def get_mongodb_connection() -> MongoDBConnection:
    """
    Get a cached instance of our database connection.
    """
    return MongoDBConnection()
