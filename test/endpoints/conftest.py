from datetime import datetime

import pymongo
import pytest_asyncio

from operationsgateway_api.src.mongo.interface import MongoDBInterface


async def add_user(auth_type):
    user = {
        "_id": f"testuserthatdoesnotexistinthedatabase{auth_type}",
        "auth_type": "",
        "authorised_routes": ["/submit/hdf POST", "/experiments POST"],
    }
    if auth_type == "fed":
        user["auth_type"] = "FedID"
    if auth_type == "local":
        user["auth_type"] = "local"
        user["sha256_password"] = (
            "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
        )
        # hashed "password"

    await MongoDBInterface.insert_one(
        "users",
        user,
    )


async def remove_user(auth_type):
    await MongoDBInterface.delete_one(
        "users",
        filter_={"_id": f"testuserthatdoesnotexistinthedatabase{auth_type}"},
    )


@pytest_asyncio.fixture(scope="function")
async def add_delete_fed_fixture():
    await add_user("fed")
    yield
    await remove_user("fed")


@pytest_asyncio.fixture(scope="function")
async def add_delete_local_fixture():
    await add_user("local")
    yield
    await remove_user("local")


@pytest_asyncio.fixture(scope="function")
async def delete_fed_fixture():
    yield
    await remove_user("fed")


@pytest_asyncio.fixture(scope="function")
async def delete_local_fixture():
    yield
    await remove_user("local")


@pytest_asyncio.fixture(scope="function")
async def remove_experiment_fixture():
    yield
    await MongoDBInterface.delete_one(
        "experiments",
        {
            "experiment_id": "20310001",
            "start_date": datetime(1920, 4, 30, 10, 0),
        },
    )


@pytest_asyncio.fixture(scope="function")
async def remove_manifest_fixture():
    yield
    filter_to_delete = await MongoDBInterface.find_one(
        "channels",
        {},
        [("_id", pymongo.DESCENDING)],
        projection=["_id"],
    )
    print(f"filter_to_delete: {filter_to_delete}")
    await MongoDBInterface.delete_one("channels", filter_to_delete)
