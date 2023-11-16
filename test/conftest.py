import base64
import io
import json

from fastapi.testclient import TestClient
import imagehash
from PIL import Image
import pytest

from operationsgateway_api.src.experiments.unique_worker import UniqueWorker
from operationsgateway_api.src.main import app
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler


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


def assert_thumbnails(record: dict, expected_thumbnails_hashes: dict):
    """
    Iterate through the record looking for the channel names that match the keys in the
    perceptual hash (phash) dictionary. As each channel is found, check that the phash of the thumbnail
    matches the expected value in the phash dictionary. Ensure all channels in the phash
    dictionary are present in the record.
    """
    num_channels_found = 0
    for channel_name, value in record["channels"].items():
        if channel_name in expected_thumbnails_hashes.keys():
            num_channels_found += 1
            b64_thumbnail_string = value["thumbnail"]
            thumbnail_bytes = base64.b64decode(b64_thumbnail_string)
            img = Image.open(io.BytesIO(thumbnail_bytes))
            thumbnail_phash = str(imagehash.phash(img))
            assert thumbnail_phash == expected_thumbnails_hashes[channel_name]
    assert num_channels_found == len(expected_thumbnails_hashes.keys())


def set_preferred_colourmap(test_app: TestClient, auth_token: str, do_it: bool):
    """
    Set the preferred colour map via the user preferences endpoint.
    Note that the 'do_it' argument allows the method to be called by all iterations of
    a test run even where it is set to false and the preference should not be set.
    """
    if do_it:
        test_app.post(
            "/user_preferences",
            content=json.dumps(
                {
                    "name": FalseColourHandler.preferred_colour_map_pref_name,
                    "value": "coolwarm",
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
            f"/user_preferences/{FalseColourHandler.preferred_colour_map_pref_name}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
