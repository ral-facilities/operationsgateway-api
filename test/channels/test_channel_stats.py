from datetime import datetime
from tempfile import SpooledTemporaryFile
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
import h5py
import pytest
import pytest_asyncio

from operationsgateway_api.src.channels.channel_stats import (
    ChannelStats,
    COLLECTION_NAME,
)
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.routes.channels import get_channel_summary
from test.conftest import RECORD_ID_TMP
from test.records.ingestion.create_test_hdf import create_test_hdf_file

CHANNEL_A = "TEST_CHANNEL_STATS_A"
CHANNEL_B = "TEST_CHANNEL_STATS_B"

# Record IDs for testing the stats on their own, which are never stored as records
ID_1 = "20230601000000000"
ID_2 = "20230602000000000"
ID_3 = "20230603000000000"
ID_4 = "20230604000000000"
ID_5 = "20230605000000000"

# Records which are stored in the database to test correcting stats after a delete
REC_1 = "19900101000000000"
REC_2 = "19900102000000000"
REC_3 = "19900103000000000"
REC_4 = "19900104000000000"
REC_5 = "19900105000000000"
ALL_RECORDS = [REC_1, REC_2, REC_3, REC_4, REC_5]

# Channels in the HDF file made by `create_test_hdf_file()`, and one added to the
# record later when testing a merge
TEST_HDF_CHANNELS = [
    "ASTRA_CONTROL_MODE_STRING",
    "CM-202-CVC-WFS",
    "CM-202-CVC-WFS-COEF",
    "PM-201-FE-CAM-1",
    "PM-201-FE-CAM-2",
    "PM-201-FE-CAM-2-CENX",
    "PM-201-FE-CAM-2-CENY",
    "PM-201-FE-CAM-2-FWHMX",
    "PM-201-FE-CAM-2-FWHMY",
    "PM-201-FE-EM",
    "PM-201-HJ-PD",
    "PM-201-PA1-EM",
    "PM-201-PA2-EM",
    "PM-201-TJ-CAM-2-CENX",
    "PM-201-TJ-CAM-2-CENY",
    "PM-201-TJ-CAM-2-FWHMX",
    "PM-201-TJ-CAM-2-FWHMY",
    "PM-201-TJ-EM",
]
ADDED_CHANNEL = "PM-201-TJ-CRY-T"

CHANNELS_WITH_STATS = [CHANNEL_A, CHANNEL_B, *TEST_HDF_CHANNELS, ADDED_CHANNEL]


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_stats_and_records():
    """
    Remove everything these tests create, before and after each one, so a failed test
    can't affect the next

    Some of the channels used are also in the ingested test data, so the stats they
    already have are put back afterwards for the tests which run after these
    """

    def stats_collection():
        # Looked up each time it's needed, rather than kept, because shutting the app
        # down closes the database connection a collection object is bound to. The
        # tests which run the app tear it down before this fixture cleans up
        return MongoDBInterface.get_collection_object(COLLECTION_NAME)

    existing_stats = (
        await stats_collection()
        .find(
            {"_id": {"$in": CHANNELS_WITH_STATS}},
        )
        .to_list(length=None)
    )

    async def remove_everything():
        await MongoDBInterface.get_collection_object("records").delete_many(
            {"_id": {"$in": ALL_RECORDS}},
        )
        await stats_collection().delete_many({"_id": {"$in": CHANNELS_WITH_STATS}})

    await remove_everything()
    yield
    await remove_everything()
    if existing_stats:
        await stats_collection().insert_many(existing_stats)


async def store_record(record_id, channel_names):
    """
    Store a minimal record in the database and update the stats like ingesting it would
    """
    await MongoDBInterface.insert_one(
        "records",
        {"_id": record_id, "channels": {name: {"data": 1} for name in channel_names}},
    )
    await ChannelStats.update_for_record(record_id, channel_names)


async def delete_record(record_id):
    """
    Delete a record from the database and correct the stats like the endpoint does
    """
    await Record.delete_record(record_id)
    await ChannelStats.remove_record(record_id)


class TestChannelStats:
    # Updates the stats of a channel for the first time, which has to create the stats
    # document, and checks the record is both the first and the newest
    @pytest.mark.asyncio
    async def test_first_record_creates_stats(self):
        await ChannelStats.update_for_record(ID_1, [CHANNEL_A])

        stats = await ChannelStats.get(CHANNEL_A)

        # Check the first record seen is both the first and the most recent
        assert stats.id_ == CHANNEL_A
        assert stats.first_record_id == ID_1
        assert stats.last_record_ids == [ID_1]

    # Updates a channel with five records and checks only the three newest are kept,
    # without affecting the first ID
    @pytest.mark.asyncio
    async def test_only_three_most_recent_records_kept(self):
        for record_id in (ID_1, ID_2, ID_3, ID_4, ID_5):
            await ChannelStats.update_for_record(record_id, [CHANNEL_A])

        stats = await ChannelStats.get(CHANNEL_A)

        # Check only the three newest are kept, while the first ID is unaffected
        assert stats.first_record_id == ID_1
        assert stats.last_record_ids == [ID_5, ID_4, ID_3]

    # Ingests an old record after newer ones, like re-ingesting an old file, and checks
    # it becomes the first ID but is left out of the newest IDs
    @pytest.mark.asyncio
    async def test_older_record_ingested_late_moves_first_id_earlier(self):
        for record_id in (ID_3, ID_4, ID_5):
            await ChannelStats.update_for_record(record_id, [CHANNEL_A])
        await ChannelStats.update_for_record(ID_1, [CHANNEL_A])

        stats = await ChannelStats.get(CHANNEL_A)

        # Check the late record becomes the first ID but, being older than the three
        # newest, doesn't appear in the recent IDs
        assert stats.first_record_id == ID_1
        assert stats.last_record_ids == [ID_5, ID_4, ID_3]

    # Ingests the same record twice and checks it isn't listed twice in the newest IDs
    @pytest.mark.asyncio
    async def test_same_record_twice_changes_nothing(self):
        await ChannelStats.update_for_record(ID_1, [CHANNEL_A])
        await ChannelStats.update_for_record(ID_2, [CHANNEL_A])
        await ChannelStats.update_for_record(ID_2, [CHANNEL_A])

        stats = await ChannelStats.get(CHANNEL_A)

        # Check re-ingesting a record doesn't add a duplicate to the recent IDs
        assert stats.first_record_id == ID_1
        assert stats.last_record_ids == [ID_2, ID_1]

    # Updates two channels from one record, then only one from a later record, and
    # checks the channel missing from the later record keeps its earlier stats
    @pytest.mark.asyncio
    async def test_only_channels_in_the_record_are_updated(self):
        await ChannelStats.update_for_record(ID_1, [CHANNEL_A, CHANNEL_B])
        await ChannelStats.update_for_record(ID_2, [CHANNEL_A])

        stats_a = await ChannelStats.get(CHANNEL_A)
        stats_b = await ChannelStats.get(CHANNEL_B)

        # Check a channel missing from the second record keeps its earlier stats
        assert stats_a.last_record_ids == [ID_2, ID_1]
        assert stats_b.first_record_id == ID_1
        assert stats_b.last_record_ids == [ID_1]


class TestRemoveRecord:
    # Deletes the newest record of a channel and checks the next older record takes
    # its place in the newest IDs
    @pytest.mark.asyncio
    async def test_newest_record_replaced_by_older_one(self):
        for record_id in ALL_RECORDS:
            await store_record(record_id, [CHANNEL_A])

        await delete_record(REC_5)

        stats = await ChannelStats.get(CHANNEL_A)

        # Check the next older record joins the newest records
        assert stats.first_record_id == REC_1
        assert stats.last_record_ids == [REC_4, REC_3, REC_2]

    # Deletes the first record of a channel and checks the first ID moves to the next
    # record, without affecting the newest IDs
    @pytest.mark.asyncio
    async def test_first_record_replaced_by_next_one(self):
        for record_id in ALL_RECORDS:
            await store_record(record_id, [CHANNEL_A])

        await delete_record(REC_1)

        stats = await ChannelStats.get(CHANNEL_A)

        # Check the first ID moves to the next record, and the newest are unaffected
        assert stats.first_record_id == REC_2
        assert stats.last_record_ids == [REC_5, REC_4, REC_3]

    # Deletes a record when the older records don't all contain the channel, and checks
    # the search for a replacement skips those that don't
    @pytest.mark.asyncio
    async def test_records_without_the_channel_are_skipped(self):
        await store_record(REC_1, [CHANNEL_A, CHANNEL_B])
        await store_record(REC_2, [CHANNEL_B])
        await store_record(REC_3, [CHANNEL_A])
        await store_record(REC_4, [CHANNEL_A, CHANNEL_B])
        await store_record(REC_5, [CHANNEL_A, CHANNEL_B])

        await delete_record(REC_4)

        stats = await ChannelStats.get(CHANNEL_B)

        # Check records without channel B (REC_3) aren't picked to fill the gap
        assert stats.last_record_ids == [REC_5, REC_2, REC_1]

    # Deletes every record containing a channel, one at a time, and checks the stats
    # shrink and are then removed once no record contains the channel
    @pytest.mark.asyncio
    async def test_deleting_last_records_with_channel_removes_stats(self):
        await store_record(REC_1, [CHANNEL_A])
        await store_record(REC_2, [CHANNEL_A])

        await delete_record(REC_1)
        stats_after_first = await ChannelStats.get(CHANNEL_A)

        # Check one record is left once the first is deleted
        assert stats_after_first.first_record_id == REC_2
        assert stats_after_first.last_record_ids == [REC_2]

        await delete_record(REC_2)

        # Check the channel's stats are removed when no record contains it any more
        assert await ChannelStats.get(CHANNEL_A) is None


def timestamp_of(record_id):
    return datetime.strptime(record_id[:14], "%Y%m%d%H%M%S")


async def store_summary_record(record_id):
    """
    Store a record with a scalar value and a date, and update the stats like ingesting
    it would. The value is the day of the month the record is dated, as a number
    """
    await MongoDBInterface.insert_one(
        "records",
        {
            "_id": record_id,
            "version": 1,
            "metadata": {
                "epac_ops_data_version": "1.0",
                "timestamp": timestamp_of(record_id),
            },
            "channels": {
                CHANNEL_A: {
                    "metadata": {"channel_dtype": "scalar"},
                    "data": float(timestamp_of(record_id).day),
                },
            },
        },
    )
    await ChannelStats.update_for_record(record_id, [CHANNEL_A])


async def get_summary():
    """
    Run the channel summary endpoint's code directly, without the web server. The user
    and their colourmaps aren't what's being tested, so they're fixed
    """
    with (
        patch(
            "operationsgateway_api.src.routes.channels.JwtHandler.get_payload",
            return_value={"username": "test_user"},
        ),
        patch(
            "operationsgateway_api.src.routes.channels.FalseColourHandler"
            ".get_preferred_colourmap",
            new_callable=AsyncMock,
            return_value="viridis",
        ),
        patch(
            "operationsgateway_api.src.routes.channels.FalseColourHandler"
            ".get_preferred_float_colourmap",
            new_callable=AsyncMock,
            return_value="bwr",
        ),
    ):
        return await get_channel_summary(channel_name=CHANNEL_A, access_token="token")


class TestChannelSummaryFromStats:
    # Gets the summary of a channel in five records and checks the dates and the three
    # newest values come from the records the stats point at
    @pytest.mark.asyncio
    async def test_summary_uses_the_stats(self):
        for record_id in ALL_RECORDS:
            await store_summary_record(record_id)

        summary = await get_summary()

        # Check the dates are those of the first and newest records, and the sample is
        # the three newest values, newest first
        assert summary.first_date == timestamp_of(REC_1)
        assert summary.most_recent_date == timestamp_of(REC_5)
        assert summary.recent_sample == [
            {timestamp_of(REC_5): 5.0},
            {timestamp_of(REC_4): 4.0},
            {timestamp_of(REC_3): 3.0},
        ]

    # Deletes the newest record of a channel and checks the summary moves on to the
    # records that are now the newest, showing the stats are corrected for it
    @pytest.mark.asyncio
    async def test_summary_after_newest_record_deleted(self):
        for record_id in ALL_RECORDS:
            await store_summary_record(record_id)
        await delete_record(REC_5)

        summary = await get_summary()

        # Check the summary now ends at the next newest record
        assert summary.most_recent_date == timestamp_of(REC_4)
        assert summary.recent_sample == [
            {timestamp_of(REC_4): 4.0},
            {timestamp_of(REC_3): 3.0},
            {timestamp_of(REC_2): 2.0},
        ]

    # Asks for the summary of a channel which has no stats and checks it is refused,
    # instead of searching the records for it
    @pytest.mark.asyncio
    async def test_channel_without_stats_is_an_error(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_summary()

        # Check the usual error for a channel with no data is given
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == f"There is no timestamp data for {CHANNEL_A}"


class TestSubmitHDFChannelStats:
    # Submits a new HDF file through the endpoint and checks every channel in it ends
    # up with stats pointing at the new record
    @pytest.mark.asyncio
    async def test_new_record_updates_channel_stats(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        _ = await create_test_hdf_file()

        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files={"file": ("test.h5", open("test.h5", "rb"))},
        )
        assert test_response.status_code == 201

        for channel_name in TEST_HDF_CHANNELS:
            stats = await ChannelStats.get(channel_name)

            # Check each channel in the new record has stats pointing at that record
            assert stats.first_record_id == RECORD_ID_TMP
            assert stats.last_record_ids == [RECORD_ID_TMP]

    # Submits an HDF file, then a second file adding one more channel to the same
    # record, and checks the added channel gets stats when the record is merged
    @pytest.mark.asyncio
    async def test_merge_updates_stats_of_added_channel(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        _ = await create_test_hdf_file()
        test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files={"file": ("test.h5", open("test.h5", "rb"))},
        )

        temporary_file = SpooledTemporaryFile()
        with h5py.File(temporary_file, "w") as f:
            f.attrs.create("epac_ops_data_version", "1.0")
            record = f["/"]
            record.attrs.create("timestamp", "2020-04-07T14:28:16+00:00")
            record.attrs.create("shotnum", 366272, dtype="u8")
            record.attrs.create("active_area", "ea1")
            record.attrs.create("active_experiment", "90097341")
            group = record.create_group(ADDED_CHANNEL)
            group.attrs.create("channel_dtype", "scalar")
            group.create_dataset("data", data=0)

        # Check the channel isn't known before the existing record is updated with it
        assert await ChannelStats.get(ADDED_CHANNEL) is None

        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files={"file": ("test.h5", temporary_file)},
        )
        assert test_response.status_code == 200

        stats = await ChannelStats.get(ADDED_CHANNEL)

        # Check the channel added by updating an existing record now has stats
        assert stats.first_record_id == RECORD_ID_TMP
        assert stats.last_record_ids == [RECORD_ID_TMP]
