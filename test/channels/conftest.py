import pytest_asyncio

from operationsgateway_api.src.mongo.interface import MongoDBInterface


@pytest_asyncio.fixture(scope="function")
async def remove_manifest_entry():
    yield
    await MongoDBInterface.delete_one(
        "channels",
        filter_={"_id": "19830222132431"},
    )
