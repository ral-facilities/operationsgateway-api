import asyncio
import base64
import io
import json
import os
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import patch

from fastapi.testclient import TestClient
import imagehash
from PIL import Image as PILImage
import pytest
import pytest_asyncio

from operationsgateway_api.src.config import BackupConfig, Config
from operationsgateway_api.src.main import app
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.echo_interface import (
    EchoInterface,
    get_echo_interface,
)
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler
from operationsgateway_api.src.records.float_image import FloatImage
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.vector import Vector
from operationsgateway_api.src.records.waveform import Waveform
from util.realistic_data.ingest_echo_data import DataIngester

MARK_EPAC_TEST = pytest.mark.skipif(
    condition=Config.config.app.use_sub_second_timestamps,
    reason="Skip EPAC style data",
)
MARK_GEMINI_TEST = pytest.mark.skipif(
    condition=not Config.config.app.use_sub_second_timestamps,
    reason="Skip Gemini style data",
)


def format_id(record_id: str) -> str:
    """
    Format `record_id` appropriately based on
    `Config.config.app.use_sub_second_timestamps`.

    Args:
        record_id (str): Record id string including ms in the form "YYYYMMDDHHMMSSfff".

    Returns:
        str:
            Record id string possibly including ms in the form "YYYYMMDDHHMMSSfff" or
            "YYYYMMDDHHMMSS".
    """
    if Config.config.app.use_sub_second_timestamps:
        return record_id
    else:
        return record_id[:14]


def format_datetime_str(datetime_str: str) -> str:
    """
    Format `datetime_str` appropriately based on
    `Config.config.app.use_sub_second_timestamps`.

    Args:
        datetime_str (str):
            Datetime string including ms in the form "YYYY-MM-DDTHH:MM:SS.ffffff".

    Returns:
        str:
            Datetime string possibly including ms in the form
            "YYYY-MM-DDTHH:MM:SS.ffffff" or "YYYY-MM-DDTHH:MM:SS".
    """
    if Config.config.app.use_sub_second_timestamps:
        return datetime_str
    else:
        return datetime_str.split(".")[0]


RECORD_ID_TMP = format_id("20200407142816000")
RECORD_ID_05_0800 = format_id("20230605080000123")
RECORD_ID_05_0803 = format_id("20230605080300234")
RECORD_ID_05_1700 = format_id("20230605170000345")
RECORD_ID_06_1200 = format_id("20230606120000456")
DATETIME_STR_05_0800 = format_datetime_str("2023-06-05T08:00:00.123000")
DATETIME_STR_05_0803 = format_datetime_str("2023-06-05T08:03:00.234000")
DATETIME_STR_05_1700 = format_datetime_str("2023-06-05T17:00:00.345000")
DATETIME_STR_06_1200 = format_datetime_str("2023-06-06T12:00:00.456000")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def ingest() -> AsyncGenerator[None, None]:
    record = await MongoDBInterface.find_one(collection_name="records")
    if record is None:
        data_ingester = DataIngester()
        data_ingester.main()

    yield

    # Session tear down code could go here, if needed


@pytest.fixture(scope="function")
def test_app():
    """
    Using TestClient as a context manager runs the lifespan and initialises our
    EchoInterface like it would be in production.
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def test_app_backup_enabled(tmp_path: Path):
    """
    Using TestClient as a context manager runs the lifespan and initialises our
    EchoInterface like it would be in production.
    """
    cache_directory = tmp_path / "cache"
    cache_directory.mkdir()
    keytab_file_path = tmp_path / ".keytab"
    keytab_file_path.write_text("")
    keytab_file_path.chmod(0o600)
    backup = BackupConfig(
        cache_directory=str(cache_directory),
        target_url="",
        copy_cron_string="* * * * *",
        worker_file_path=str(tmp_path / "worker"),
        keytab_file_path=str(keytab_file_path),
    )

    with (
        patch("operationsgateway_api.src.config.Config.config.backup", backup),
        TestClient(app) as client,
    ):
        yield client


@pytest.fixture()
def login_and_get_token(test_app: TestClient):
    json = '{"username": "backend", "password": "back"}'
    response = test_app.post("/login", content=json)
    # strip the first and last characters off the response
    # (the double quotes that surround it)
    token = response.text[1:-1]
    return token


@pytest.fixture()
def login_as_frontend_and_get_token(test_app: TestClient):
    json = '{"username": "frontend", "password": "front"}'
    response = test_app.post("/login", content=json)
    # strip the first and last characters off the response
    # (the double quotes that surround it)
    token = response.text[1:-1]
    return token


@pytest.fixture()
def remove_background_pid_file():
    """
    Remove background file for experiments task after tests relating to it have run
    """
    yield

    try:
        os.remove("test/path")
    except FileNotFoundError:
        pass


async def remove_record(timestamp_id):
    await MongoDBInterface.delete_one(
        "records",
        filter_={"_id": f"{timestamp_id}"},
    )


@pytest_asyncio.fixture(scope="function")
async def reset_record_storage():
    yield
    await remove_record(RECORD_ID_TMP)
    await MongoDBInterface.delete_one("records", {"metadata.shotnum": 366272})
    echo = EchoInterface()
    subdirectories = echo.format_record_id(RECORD_ID_TMP)
    await echo.delete_directory(f"{Waveform.echo_prefix}/{subdirectories}/")
    await echo.delete_directory(f"{Image.echo_prefix}/{subdirectories}/")
    await echo.delete_directory(f"{FloatImage.echo_prefix}/{subdirectories}/")
    await echo.delete_directory(f"{Vector.echo_prefix}/{subdirectories}/")

    if os.path.exists("test.h5"):
        os.remove("test.h5")


def assert_record(record, expected_channel_count, expected_channel_data):
    assert list(record.keys()) == ["_id", "metadata", "channels"]
    assert len(record["channels"]) == expected_channel_count

    test_channel_name = list(expected_channel_data.keys())[0]
    channel_found = False
    for channel_name, value in record["channels"].items():
        assert "variable_value" not in value  # Should never be included in response
        if channel_name == test_channel_name:
            channel_found = True
            if "data" in value:
                assert value["data"] == expected_channel_data[channel_name]
            else:
                image_bytes = base64.b64decode(value["thumbnail"])
                image = PILImage.open(io.BytesIO(image_bytes))
                image_phash = str(imagehash.phash(image))
                assert image_phash == expected_channel_data[channel_name]

    if not channel_found:
        raise AssertionError("Expected channel not found")


def assert_thumbnails(record: dict, expected_thumbnails_hashes: dict):
    """
    Iterate through the record looking for the channel names that match the keys in the
    perceptual hash (phash) dictionary. As each channel is found, check that the phash
    of the thumbnail matches the expected value in the phash dictionary. Ensure all
    channels in the phash dictionary are present in the record.
    """
    num_channels_found = 0
    for channel_name, value in record["channels"].items():
        if channel_name in expected_thumbnails_hashes.keys():
            num_channels_found += 1
            b64_thumbnail_string = value["thumbnail"]
            thumbnail_bytes = base64.b64decode(b64_thumbnail_string)
            img = PILImage.open(io.BytesIO(thumbnail_bytes))
            thumbnail_phash = str(imagehash.phash(img))
            assert thumbnail_phash == expected_thumbnails_hashes[channel_name]
    assert num_channels_found == len(expected_thumbnails_hashes.keys())


def assert_text_file_contents(
    filepath: str,
    file_contents: list[bytes],
    sort_lines: bool = False,
) -> None:
    """
    Check that the text file at the given filepath contains the contents specified
    """
    with open(f"{os.path.dirname(os.path.realpath(__file__))}/{filepath}", "rb") as f:
        test_file_contents = f.readlines()

    if sort_lines:
        file_contents.sort()

    assert test_file_contents == file_contents


def set_preferred_colourmap(test_app: TestClient, auth_token: str, do_it: bool):
    """
    Set the preferred colour map via the user preferences endpoint.
    Note that the 'do_it' argument allows the method to be called by all iterations of
    a test run even where it is set to false and the preference should not be set.
    """
    if do_it:
        test_app.post(
            "/users/preferences",
            content=json.dumps(
                {
                    "name": FalseColourHandler.preferred_colour_map_pref_name,
                    "value": "coolwarm",
                },
            ),
            headers={"Authorization": f"Bearer {auth_token}"},
        )


def set_preferred_float_colourmap(test_app: TestClient, auth_token: str, do_it: bool):
    """
    Set the preferred float colour map via the user preferences endpoint.
    Note that the 'do_it' argument allows the method to be called by all iterations of
    a test run even where it is set to false and the preference should not be set.
    """
    if do_it:
        test_app.post(
            "/users/preferences",
            content=json.dumps(
                {
                    "name": FalseColourHandler.preferred_float_colour_map_pref_name,
                    "value": "vanimo",
                },
            ),
            headers={"Authorization": f"Bearer {auth_token}"},
        )


def unset_preferred_colourmap(test_app: TestClient, auth_token: str, do_it: bool):
    """
    Unset the preferred colour map via the user preferences endpoint.
    """
    if do_it:
        test_app.delete(
            f"/users/preferences/{FalseColourHandler.preferred_colour_map_pref_name}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )


def unset_preferred_float_colourmap(test_app: TestClient, auth_token: str, do_it: bool):
    """
    Unset the preferred float colour map via the user preferences endpoint.
    """
    if do_it:
        test_app.delete(
            f"/users/preferences/{FalseColourHandler.preferred_float_colour_map_pref_name}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )


@pytest.fixture(scope="function")
def clear_cached_echo_interface() -> None:
    """
    Clear the cache between tests to ensure we do not share the same event loop between
    tests, as this gets closed.
    """
    get_echo_interface.cache_clear()
