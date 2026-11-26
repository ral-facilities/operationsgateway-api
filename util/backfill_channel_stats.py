"""
Fill the channel stats collection from the records already in the database, so channel
summaries don't have to search for the first and most recent record of each channel.

To run it, set DATABASE_URL and DATABASE_NAME below, then from the root of the repo:
    poetry run python util/backfill_channel_stats.py
"""

import logging
from time import time

from pymongo import MongoClient

from operationsgateway_api.src.channels.channel_stats import (
    ChannelStats,
    COLLECTION_NAME,
    NUM_RECENT_RECORDS,
)

DATABASE_URL = (
    "mongodb://username:password@host1:27017,host2:27017,host3:27017/"
    "?authMechanism=SCRAM-SHA-256&authSource=admin&replicaSet=replica_set"
    "&readPreference=secondaryPreferred"
)
DATABASE_NAME = "OpsGateway_gemini_scratch"

# Errors are written here, progress is printed to the screen
LOG_FILE = "backfill_channel_stats.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="[%(asctime)s] %(message)s",
)


def pipeline(year: int) -> list:
    """
    Find the first and newest records containing each channel, for one year of records
    """

    return [
        {"$match": {"_id": {"$gte": str(year), "$lt": str(year + 1)}}},
        {
            "$project": {
                "names": {
                    "$map": {
                        "input": {"$objectToArray": "$channels"},
                        "in": "$$this.k",
                    },
                },
            },
        },
        {"$unwind": "$names"},
        {
            "$group": {
                "_id": "$names",
                "first_record_id": {"$min": "$_id"},
                "last_record_ids": {
                    "$topN": {
                        "n": NUM_RECENT_RECORDS,
                        "sortBy": {"_id": -1},
                        "output": "$_id",
                    },
                },
            },
        },
    ]


def years_of_records(records) -> range:
    """
    The years the records cover, found from the oldest and newest record IDs.
    """

    oldest = records.find_one(sort=[("_id", 1)], projection=["_id"])
    newest = records.find_one(sort=[("_id", -1)], projection=["_id"])
    if not oldest:
        return range(0)

    return range(int(oldest["_id"][:4]), int(newest["_id"][:4]) + 1)


try:
    print(f"Starting on {DATABASE_NAME}, reading a year of records at a time")
    database = MongoClient(DATABASE_URL)[DATABASE_NAME]
    records = database["records"]
    collection = database[COLLECTION_NAME]

    # A year at a time
    for year in years_of_records(records):
        start_time = time()
        stats = list(records.aggregate(pipeline(year), allowDiskUse=True))

        for channel in stats:
            record_ids = {channel["first_record_id"], *channel["last_record_ids"]}
            for record_id in sorted(record_ids):
                collection.update_one(
                    {"_id": channel["_id"]},
                    ChannelStats.update_pipeline(record_id),
                    upsert=True,
                )

        channels = f"{len(stats)} channels" if stats else "no records"
        print(f"{year}: {channels} in {time() - start_time:.1f} seconds")

    print(f"Stats are stored for {collection.count_documents({})} channels")
except Exception:
    logging.exception("Backfill of %r failed", DATABASE_NAME)
    print(f"Failed, see {LOG_FILE}")
    raise
