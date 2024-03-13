import pytest_asyncio

from operationsgateway_api.src.mongo.interface import MongoDBInterface


@pytest_asyncio.fixture(scope="function")
async def remove_record_entry():
    yield
    await MongoDBInterface.delete_one(
        "records",
        filter_={"_id": "19520605070023"},
    )
