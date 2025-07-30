from datetime import datetime
from io import BytesIO
import os

import numpy as np
import pymongo
import pytest
import pytest_asyncio

from operationsgateway_api.src.auth.authentication import Authentication
from operationsgateway_api.src.models import VectorModel, WaveformModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.echo_interface import EchoInterface
from operationsgateway_api.src.records.float_image import FloatImage
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.records.vector import Vector
from operationsgateway_api.src.records.waveform import Waveform


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


async def remove_record(timestamp_id):
    await MongoDBInterface.delete_one(
        "records",
        filter_={"_id": f"{timestamp_id}"},
    )


@pytest_asyncio.fixture(scope="function")
async def reset_record_storage():
    yield
    record_id = "20200407142816"
    await remove_record(record_id)
    echo = EchoInterface()
    subdirectories = echo.format_record_id(record_id)
    echo.delete_directory(f"{Waveform.echo_prefix}/{subdirectories}/")
    echo.delete_directory(f"{Image.echo_prefix}/{subdirectories}/")
    echo.delete_directory(f"{FloatImage.echo_prefix}/{subdirectories}/")
    echo.delete_directory(f"{Vector.echo_prefix}/{subdirectories}/")

    if os.path.exists("test.h5"):
        os.remove("test.h5")


@pytest_asyncio.fixture(scope="function")
async def remove_manifest_fixture():
    yield
    filter_to_delete = await MongoDBInterface.find_one(
        "channels",
        {},
        [("_id", pymongo.DESCENDING)],
        projection=["_id"],
    )
    await MongoDBInterface.delete_one("channels", filter_to_delete)


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
async def record_for_delete_records():
    record_id = "19000000000011"
    test_record = {
        "_id": record_id,
        "metadata": {
            "epac_ops_data_version": "1.0",
            "shotnum": 423648000000,
            "timestamp": "2023-06-05T08:00:00",
        },
        "channels": {
            "test-scalar-channel-id": {
                "metadata": {"channel_dtype": "scalar", "units": "µm"},
                "data": 5.126920467610521,
            },
            "test-image-channel-id": {
                "metadata": {"channel_dtype": "image"},
                "image_path": f"{record_id}/test-image-channel-id.png",
                "thumbnail": "i5~9=",
            },
            "test-waveform-channel-id": {
                "metadata": {"channel_dtype": "waveform"},
                "waveform_path": f"{record_id}/test-waveform-channel-id.json",
                "thumbnail": "i5~9=",
            },
        },
    }

    record_instance = Record(test_record)
    await record_instance.insert()

    yield record_id

    await Record.delete_record(record_id)


@pytest_asyncio.fixture(scope="function")
async def data_for_delete_records(record_for_delete_records: str):
    echo = EchoInterface()
    image_file = "test-image-channel-id.png"
    image_path = f"{Image.echo_prefix}/{record_for_delete_records}/{image_file}"
    with open("test/images/original_image.png", "rb") as f:
        echo.upload_file_object(f, image_path)

    waveform = Waveform(WaveformModel(x=[1.0, 2.0, 3.0], y=[1.0, 2.0, 3.0]))
    waveform_bytes = waveform.to_json()
    waveform_file = "test-waveform-channel-id.json"
    waveform_path = (
        f"{Waveform.echo_prefix}/{record_for_delete_records}/{waveform_file}"
    )
    echo.upload_file_object(waveform_bytes, waveform_path)

    bytes_io = BytesIO()
    np.savez_compressed(bytes_io, np.ones((1, 1)))
    filename = "test-float-image-channel-id.npz"
    float_image_path = (
        f"{FloatImage.echo_prefix}/{record_for_delete_records}/{filename}"
    )
    echo.upload_file_object(bytes_io, float_image_path)

    vector = Vector(VectorModel(data=[1.0], path=""))
    bytes_io = BytesIO(vector.vector.model_dump_json(indent=2).encode())
    filename = "test-vector-channel-id.json"
    vector_path = f"{vector.echo_prefix}/{record_for_delete_records}/{filename}"
    echo.upload_file_object(bytes_io, vector_path)

    yield record_for_delete_records

    await Record.delete_record(record_for_delete_records)
    echo.delete_file_object(image_path)
    echo.delete_file_object(waveform_path)
    echo.delete_file_object(float_image_path)
    echo.delete_file_object(vector_path)


@pytest_asyncio.fixture(scope="function")
async def data_for_delete_records_subdirectories(record_for_delete_records: str):
    echo = EchoInterface()
    subdirectories = EchoInterface.format_record_id(record_for_delete_records)
    image_file = "test-image-channel-id.png"
    image_path = f"{Image.echo_prefix}/{subdirectories}/{image_file}"
    with open("test/images/original_image.png", "rb") as f:
        echo.upload_file_object(f, image_path)

    waveform = Waveform(WaveformModel(x=[1.0, 2.0, 3.0], y=[1.0, 2.0, 3.0]))
    waveform_bytes = waveform.to_json()
    waveform_file = "test-waveform-channel-id.json"
    waveform_path = f"{Waveform.echo_prefix}/{subdirectories}/{waveform_file}"
    echo.upload_file_object(waveform_bytes, waveform_path)

    bytes_io = BytesIO()
    np.savez_compressed(bytes_io, np.ones((1, 1)))
    filename = "test-float-image-channel-id.npz"
    float_image_path = f"{FloatImage.echo_prefix}/{subdirectories}/{filename}"
    echo.upload_file_object(bytes_io, float_image_path)

    vector = Vector(VectorModel(data=[1.0], path=""))
    bytes_io = BytesIO(vector.vector.model_dump_json(indent=2).encode())
    filename = "test-vector-channel-id.json"
    vector_path = f"{vector.echo_prefix}/{subdirectories}/{filename}"
    echo.upload_file_object(bytes_io, vector_path)

    yield record_for_delete_records

    await Record.delete_record(record_for_delete_records)
    echo.delete_file_object(image_path)
    echo.delete_file_object(waveform_path)
    echo.delete_file_object(float_image_path)
    echo.delete_file_object(vector_path)
