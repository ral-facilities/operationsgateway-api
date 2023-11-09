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
        user["password"] = "password"
    
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
