import asyncio

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.main import app
from operationsgateway_api.src.mongo.interface import MongoDBInterface


@pytest.fixture()
def test_app():
    return TestClient(app)


@pytest.fixture()
def login_and_get_token(test_app: TestClient):
    json = '{"username": "backend", "password": "back"}'
    response = test_app.post("/login", content=json)
    # strip the first and last characters off the response
    # (the double quotes that surround it)
    token = response.text[1:-1]
    return token


@pytest.fixture()
def loop():
    # allows the testing of asynchronus functions using an event loop

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def add_fed_user(loop: asyncio.AbstractEventLoop):
    try:
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
    except BaseException:
        pass


def add_local_user(loop: asyncio.AbstractEventLoop):
    try:
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
    except BaseException:
        pass


def remove_fed_user(loop: asyncio.AbstractEventLoop):
    try:
        loop.run_until_complete(
            MongoDBInterface.delete_one(
                "users",
                filter_={"_id": "testuserthatdoesnotexistinthedatabasefed"},
            ),
        )
    except BaseException:
        pass


def remove_local_user(loop: asyncio.AbstractEventLoop):
    try:
        loop.run_until_complete(
            MongoDBInterface.delete_one(
                "users",
                filter_={"_id": "testuserthatdoesnotexistinthedatabaselocal"},
            ),
        )
    except BaseException:
        pass


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


# TODO make sure db stuff doesn't fail (try except finally possibly)
# TODO check _id isn't in database first
