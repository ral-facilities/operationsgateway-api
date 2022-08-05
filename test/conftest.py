from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.main import app


@pytest.fixture()
def test_app():
    return TestClient(app)


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
