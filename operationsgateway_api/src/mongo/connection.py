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

    # TODO - could clean this up, so you don't store collection objects here
    records = db[Config.config.mongodb.collection_name]
    images = db["images"]
    waveforms = db["waveforms"]


class ConnectionInstance:
    """
    Class containing the database connection as a class variable so it can be mocked
    during testing
    """

    db_connection = MongoDBConnection()
