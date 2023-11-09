import asyncio

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.main import app
from operationsgateway_api.src.mongo.interface import MongoDBInterface


@pytest.fixture()
def loop():
    # allows the testing of asynchronus functions using an event loop

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def add_fed_user(loop: asyncio.AbstractEventLoop):
    user = {
        "_id": "testuserthatdoesnotexistinthedatabasefed",
        "auth_type": "FedID",
        "authorised_routes": ["/submit/hdf POST", "/experiments POST"],
    }
    loop.run_until_complete(
        MongoDBInterface.insert_one(
            "users",
            user,
        ),
    )


def add_local_user(loop: asyncio.AbstractEventLoop):
    user = {
        "_id": "testuserthatdoesnotexistinthedatabaselocal",
        "auth_type": "local",
        "authorised_routes": ["/submit/hdf POST", "/experiments POST"],
        "sha256_password": "password",
    }
    loop.run_until_complete(
        MongoDBInterface.insert_one(
            "users",
            user,
        ),
    )


def remove_fed_user(loop: asyncio.AbstractEventLoop):
    loop.run_until_complete(
        MongoDBInterface.delete_one(
            "users",
            filter_={"_id": "testuserthatdoesnotexistinthedatabasefed"},
        ),
    )


def remove_local_user(loop: asyncio.AbstractEventLoop):
    loop.run_until_complete(
        MongoDBInterface.delete_one(
            "users",
            filter_={"_id": "testuserthatdoesnotexistinthedatabaselocal"},
        ),
    )


@pytest.fixture(scope="function")
def add_delete_fed_fixture(loop: asyncio.AbstractEventLoop):
    add_fed_user(loop)
    yield
    remove_fed_user(loop)


@pytest.fixture(scope="function")
def add_delete_local_fixture(loop: asyncio.AbstractEventLoop):
    add_local_user(loop)
    yield
    remove_local_user(loop)


@pytest.fixture(scope="function")
def delete_fed_fixture(loop: asyncio.AbstractEventLoop):
    yield
    remove_fed_user(loop)


@pytest.fixture(scope="function")
def delete_local_fixture(loop: asyncio.AbstractEventLoop):
    yield
    remove_local_user(loop)
