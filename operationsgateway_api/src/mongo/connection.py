import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

from operationsgateway_api.src.config import Config


class MongoDBConnection:
    """
    Class to store database connections, the database and collection
    """

    mongo_client = AsyncIOMotorClient(Config.config.mongodb.mongodb_url)
    mongo_client.get_io_loop = asyncio.get_event_loop

    db = mongo_client[Config.config.mongodb.database_name]


class ConnectionInstance:
    """
    Class containing the database connection as a class variable so it can be mocked
    during testing
    """

    db_connection = MongoDBConnection()
