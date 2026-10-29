import json

from fastapi.testclient import TestClient
import h5py
import numpy as np
import pytest
import pytest_asyncio

from operationsgateway_api.src.mongo.interface import MongoDBInterface
from test.conftest import RECORD_ID_TMP

# Prefixed so these can be told apart from any tags already in the database
TEST_TAGS = [
    {"name": "test_tripped", "description": "It tripped", "active": True},
    {"name": "test_failed", "description": "It failed", "active": True},
    {"name": "test_retired", "description": "No longer used", "active": False},
]


@pytest_asyncio.fixture(scope="function")
async def tags_fixture():
    await MongoDBInterface.insert_many("tags", TEST_TAGS)
    yield
    for tag in TEST_TAGS:
        await MongoDBInterface.delete_one("tags", {"name": tag["name"]})


def create_tagged_hdf(*tags):
    """
    Creates a small HDF file with a single scalar channel, so nothing needs uploading
    to Echo, and a `tags` attribute holding the given tags (which can be none)
    """
    with h5py.File("test.h5", "w") as f:
        f.attrs.create("epac_ops_data_version", "1.0")
        record = f["/"]
        record.attrs.create("timestamp", "2020-04-07T14:28:16+00:00")
        record.attrs.create("shotnum", 366272, dtype="u8")
        record.attrs.create("active_area", "ea1")
        record.attrs.create("active_experiment", "90097341")
        record.attrs.create("tags", np.array(tags, dtype=h5py.string_dtype()))

        scalar = record.create_group("PM-201-TJ-CRY-T")
        scalar.attrs.create("channel_dtype", "scalar")
        scalar.create_dataset("data", data=0)


async def get_stored_tags():
    record = await MongoDBInterface.find_one("records", {"_id": RECORD_ID_TMP})
    return record["metadata"].get("tags") if record else None


class TestTags:
    @pytest.mark.asyncio
    async def test_ingest_stores_tags(
        self,
        reset_record_storage,
        tags_fixture,
        test_app: TestClient,
        login_and_get_token,
    ):
        create_tagged_hdf("test_tripped", "test_failed", "test_tripped")

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}
        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        # Check the tags in the file are stored on the record, and the repeated tag
        # is only stored once
        assert test_response.status_code == 201
        assert await get_stored_tags() == ["test_tripped", "test_failed"]

    @pytest.mark.asyncio
    async def test_empty_tags_clear_existing_tags(
        self,
        reset_record_storage,
        tags_fixture,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_file = "test.h5"

        create_tagged_hdf("test_tripped")
        files = {"file": (test_file, open(test_file, "rb"))}
        test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )
        assert await get_stored_tags() == ["test_tripped"]

        create_tagged_hdf()
        files = {"file": (test_file, open(test_file, "rb"))}
        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        # Check ingesting the record again with no tags clears the stored tags
        assert test_response.status_code == 200
        assert await get_stored_tags() == []

    @pytest.mark.asyncio
    async def test_unknown_tag_is_rejected(
        self,
        reset_record_storage,
        tags_fixture,
        test_app: TestClient,
        login_and_get_token,
    ):
        create_tagged_hdf("test_tripped", "not_a_tag")

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}
        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        # Check the file is rejected, naming the unknown tag, and nothing is stored
        assert test_response.status_code == 400
        assert test_response.json() == {
            "detail": "Unrecognised or inactive tags: not_a_tag",
        }
        assert await get_stored_tags() is None

    @pytest.mark.parametrize(
        "filter_tag, expected_ids",
        [
            pytest.param("test_tripped", [RECORD_ID_TMP], id="record has the tag"),
            pytest.param("test_failed", [], id="record does not have the tag"),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_record_by_tag(
        self,
        filter_tag,
        expected_ids,
        reset_record_storage,
        tags_fixture,
        test_app: TestClient,
        login_and_get_token,
    ):
        create_tagged_hdf("test_tripped")

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}
        headers = {"Authorization": f"Bearer {login_and_get_token}"}
        test_app.post("/submit/hdf", headers=headers, files=files)

        conditions = json.dumps({"metadata.tags": {"$all": [filter_tag]}})
        test_response = test_app.get(
            "/records",
            headers=headers,
            params={"conditions": conditions},
        )

        # Check filtering by a tag returns only the records carrying that tag
        assert test_response.status_code == 200
        assert [record["_id"] for record in test_response.json()] == expected_ids

    def test_get_tags_includes_retired_tags(
        self,
        tags_fixture,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_response = test_app.get(
            "/tags",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )
        assert test_response.status_code == 200

        # Check the retired tag is included and flagged as not active, and the tags
        # are in name order
        test_tags = [
            tag for tag in test_response.json() if tag["name"].startswith("test_")
        ]
        assert test_tags == [
            {"name": "test_failed", "description": "It failed", "active": True},
            {"name": "test_retired", "description": "No longer used", "active": False},
            {"name": "test_tripped", "description": "It tripped", "active": True},
        ]
