import os

import pytest
import pytest_asyncio

from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.echo_interface import EchoInterface


def delete_hdf_file():
    if os.path.exists("test.h5"):
        os.remove("test.h5")


async def remove_record(timestamp_id):
    await MongoDBInterface.delete_one(
        "records",
        filter_={"_id": f"{timestamp_id}"},
    )


async def remove_waveform():
    await MongoDBInterface.delete_one(
        "waveforms",
        filter_={"_id": "20200407142816_PM-201-HJ-PD"},
    )


async def remove_image(images):
    echo = EchoInterface()
    for image_path in images:
        echo.delete_file_object(image_path)


@pytest.fixture(scope="function")
def remove_hdf_file():
    yield
    delete_hdf_file()


@pytest_asyncio.fixture(scope="function")
async def reset_databases():
    yield
    await remove_record("20200407142816")
    await remove_image(
        ["20200407142816/PM-201-FE-CAM-1.png", "20200407142816/PM-201-FE-CAM-2.png"],
    )
    await remove_waveform()
    delete_hdf_file()
