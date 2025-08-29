import os

import pytest
import pytest_asyncio

from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.echo_interface import EchoInterface


@pytest.fixture(scope="function")
def remove_hdf_file():
    yield
    if os.path.exists("test.h5"):
        os.remove("test.h5")


@pytest_asyncio.fixture(scope="function")
async def remove_record_entry():
    yield
    await MongoDBInterface.delete_one(
        "records",
        filter_={"_id": "19520605070023"},
    )


@pytest_asyncio.fixture(scope="function")
async def remove_test_objects():
    yield
    echo = EchoInterface()
    await echo.delete_file_object(
        "images/19520605070023/test-channel-name.png",
    )
    await echo.delete_file_object(
        "images/1952/06/05/070023/test-channel-name.png",
    )
    await echo.delete_file_object(
        "waveforms/19520605070023/test-channel-name.json",
    )
    await echo.delete_file_object(
        "waveforms/1952/06/05/070023/test-channel-name.json",
    )
