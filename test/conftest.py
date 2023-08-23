import base64
import hashlib

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.experiments.unique_worker import UniqueWorker
from operationsgateway_api.src.main import app


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
def remove_background_pid_file():
    """
    Remove background file for experiments task after tests relating to it have run
    """
    yield

    UniqueWorker.remove_file()


def assert_record(record, expected_channel_count, expected_channel_data):
    assert list(record.keys()) == ["_id", "metadata", "channels"]
    assert len(record["channels"]) == expected_channel_count

    test_channel_name = list(expected_channel_data.keys())[0]
    channel_found = False
    for channel_name, value in record["channels"].items():
        if channel_name == test_channel_name:
            channel_found = True
            assert value["data"] == expected_channel_data[channel_name]

    if not channel_found:
        raise AssertionError("Expected channel not found")


def assert_thumbnails(record: dict, expected_thumbnail_md5s: dict):
    """
    Iterate through the record looking for the channel names that match the keys in the
    md5s dictionary. As each channel is found, check that the md5sum of the thumbnail
    matches the expected value in the md5s dictionary. Ensure all channels in the md5s
    dictionary are present in the record.
    """
    num_channels_found = 0
    for channel_name, value in record["channels"].items():
        if channel_name in expected_thumbnail_md5s.keys():
            num_channels_found += 1
            b64_thumbnail_string = value["thumbnail"]
            thumbnail_bytes = base64.b64decode(b64_thumbnail_string)
            thumbnail_md5sum = hashlib.md5(thumbnail_bytes).hexdigest()
            assert thumbnail_md5sum == expected_thumbnail_md5s[channel_name]
    assert num_channels_found == len(expected_thumbnail_md5s.keys())
