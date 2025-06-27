import asyncio

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from operationsgateway_api.src.config import Config


class MongoDBConnection:
    """
    Class to store database connections, the database and collection
    """

    mongo_client = AsyncIOMotorClient(Config.config.mongodb.mongodb_url.get_secret_value())
    mongo_client.get_io_loop = asyncio.get_event_loop

    db: AsyncIOMotorDatabase = mongo_client[Config.config.mongodb.database_name]


class ConnectionInstance:
    """
    Class containing the database connection as a class variable so it can be mocked
    during testing
    """

    db_connection = MongoDBConnection()
