import logging
from typing import Any, Dict, Iterable, List, Optional

import pymongo

from operationsgateway_api.src.exceptions import DatabaseError
from operationsgateway_api.src.models import ChannelStatsModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface

log = logging.getLogger()

COLLECTION_NAME = "channel_stats"
NUM_RECENT_RECORDS = 3

# Stats are changed by MongoDB itself, using an aggregation pipeline, so two records
# being ingested at once can't overwrite each other's change. A pipeline is built from
# expressions, which the small functions below name so the pipelines read as a list of
# steps. Each takes and returns either a field reference (like "$first_record_id") or an
# expression, and `record_ids` is always an array of record IDs


def _recent_ids() -> Dict[str, Any]:
    """The channel's current newest record IDs, or none if it has no stats yet"""
    return {"$ifNull": ["$last_record_ids", []]}


def _earlier_of(first_record_id: str, record_id: str) -> Dict[str, Any]:
    """The earlier ID of the two. A missing first ID is ignored, so a channel's first
    record becomes its first ID"""
    return {"$min": [first_record_id, record_id]}


def _with_ids(record_ids: Any, extra_ids: Any) -> Dict[str, Any]:
    """`record_ids` and `extra_ids` together, without duplicates"""
    return {"$setUnion": [record_ids, extra_ids]}


def _without_id(record_ids: Any, record_id: str) -> Dict[str, Any]:
    """`record_ids` with `record_id` taken out"""
    return {"$setDifference": [record_ids, [record_id]]}


def _newest(record_ids: Any) -> Dict[str, Any]:
    """The newest `NUM_RECENT_RECORDS` of `record_ids`, newest first"""
    return {
        "$slice": [
            {"$sortArray": {"input": record_ids, "sortBy": -1}},
            NUM_RECENT_RECORDS,
        ],
    }


def _replace_id(field: str, old_id: str, new_id: str) -> Dict[str, Any]:
    """The value of `field`, with `new_id` in its place if it's `old_id`"""
    return {"$cond": [{"$eq": [field, old_id]}, new_id, field]}


class ChannelStats:
    """
    Keeps track of the first and most recent records that contain each channel, stored
    as one document per channel (the `_id` being the channel name)

    Record IDs are strings which sort in the same order as the records' timestamps, so
    comparing them as strings gives the same result as comparing the dates
    """

    @staticmethod
    def update_pipeline(record_id: str) -> List[Dict[str, Any]]:
        """
        Build the update which adds a record to a channel's stats. The same update is
        used when ingesting and when back populating, so the two agree

        It sets the channel's:
        - first record to the earlier of its current first record and this one. That
          can move it earlier, if an old record is ingested after newer ones
        - newest records to the current newest plus this one, keeping the newest few.
          Adding a record already listed changes nothing, so ingesting the same record
          twice is harmless
        """

        return [
            {
                "$set": {
                    "first_record_id": _earlier_of("$first_record_id", record_id),
                    "last_record_ids": _newest(
                        _with_ids(_recent_ids(), [record_id]),
                    ),
                },
            },
        ]

    @staticmethod
    async def update_for_record(record_id: str, channel_names: Iterable[str]) -> None:
        """
        Update the stats of every channel in a record that has just been stored

        Each channel is a separate update for now, which could be sent to MongoDB as
        one bulk write instead
        """

        pipeline = ChannelStats.update_pipeline(record_id)

        log.debug("Updating channel stats for record %s", record_id)
        for channel_name in channel_names:
            await MongoDBInterface.update_one(
                COLLECTION_NAME,
                {"_id": channel_name},
                pipeline,  # type: ignore[arg-type]  # A pipeline is a list, not a dict
                upsert=True,
            )

    @staticmethod
    async def update_for_stored_record(
        record_id: str,
        channel_names: Iterable[str],
    ) -> None:
        """
        Update the stats of every channel in a record that has just been stored, as
        `update_for_record()` does, but log a failure instead of raising it

        The record is already saved at this point, so failing the request would report
        an error for data that is stored. Ingesting the record again, or re-running the
        back population, corrects any stats that were missed
        """

        try:
            await ChannelStats.update_for_record(record_id, channel_names)
        except DatabaseError:
            log.exception("Failed to update channel stats for record %s", record_id)

    @staticmethod
    async def get(channel_name: str) -> Optional[ChannelStatsModel]:
        """
        Get a channel's stats, or `None` if the channel has no stats (which means no
        stored record contains it, or that stats haven't been back populated yet)
        """

        stats_dict = await MongoDBInterface.find_one(
            COLLECTION_NAME,
            filter_={"_id": channel_name},
        )

        return ChannelStatsModel(**stats_dict) if stats_dict else None

    @staticmethod
    async def remove_record(record_id: str) -> None:
        """
        Correct the stats of every channel which referred to a record that has just
        been deleted. Stats only hold the first and newest records of a channel, so a
        channel that doesn't refer to the record is unaffected

        The record must be deleted first, or it could be chosen as its own replacement.
        A channel stops referring to the record once it has been corrected, so if this
        fails part way through, running it again finishes the remaining channels. The
        affected channels are read through a cursor as a record can be the first or
        newest for more channels than the query limit
        """

        log.debug("Correcting channel stats after deleting record %s", record_id)
        affected_channels = MongoDBInterface.find(
            COLLECTION_NAME,
            filter_={
                "$or": [
                    {"first_record_id": record_id},
                    {"last_record_ids": record_id},
                ],
            },
        )
        async for stats_dict in affected_channels:
            await ChannelStats._correct_after_delete(
                ChannelStatsModel(**stats_dict),
                record_id,
            )

    @staticmethod
    async def _correct_after_delete(stats: ChannelStatsModel, record_id: str) -> None:
        """
        Correct one channel's stats after `record_id` was deleted

        The stats are updated using the values stored when the update runs, not those
        read here, so a record ingested in the meantime isn't lost
        """

        channel_name = stats.id_
        remaining_ids = [id_ for id_ in stats.last_record_ids if id_ != record_id]
        # With fewer than `NUM_RECENT_RECORDS` listed, every record with the channel is
        # listed, so there are no other records to search for
        list_is_complete = len(stats.last_record_ids) < NUM_RECENT_RECORDS

        replacements = []
        if not list_is_complete:
            replacements = await ChannelStats._find_older_ids(
                channel_name,
                remaining_ids,
            )

        new_recent_ids = _newest(
            _with_ids(_without_id(_recent_ids(), record_id), replacements),
        )
        set_fields = {"last_record_ids": new_recent_ids}

        if stats.first_record_id == record_id:
            new_first_id = await ChannelStats._find_new_first_id(
                channel_name,
                record_id,
                remaining_ids,
                list_is_complete,
            )

            if new_first_id is None:
                await ChannelStats._remove_stats_if_empty(channel_name, record_id)
                return

            set_fields["first_record_id"] = _replace_id(
                "$first_record_id",
                record_id,
                new_first_id,
            )

        await MongoDBInterface.update_one(
            COLLECTION_NAME,
            {"_id": channel_name},
            [{"$set": set_fields}],  # type: ignore[arg-type]
        )

    @staticmethod
    async def _find_older_ids(
        channel_name: str,
        remaining_ids: List[str],
    ) -> List[str]:
        """
        Find the records which fill the places in a channel's newest records left by a
        deleted one. They're the next records older than the oldest one still listed
        """

        missing = NUM_RECENT_RECORDS - len(remaining_ids)
        if missing <= 0:
            return []

        return await ChannelStats._find_record_ids(
            channel_name,
            {"$lt": min(remaining_ids)},
            pymongo.DESCENDING,
            missing,
        )

    @staticmethod
    async def _find_new_first_id(
        channel_name: str,
        deleted_id: str,
        remaining_ids: List[str],
        list_is_complete: bool,
    ) -> Optional[str]:
        """
        Find a channel's new first record after its old one was deleted, which is the
        next record after it, or `None` if no record contains the channel any more
        """

        if not list_is_complete:
            found_ids = await ChannelStats._find_record_ids(
                channel_name,
                {"$gt": deleted_id},
                pymongo.ASCENDING,
                1,
            )
            if found_ids:
                return found_ids[0]

        return min(remaining_ids, default=None)

    @staticmethod
    async def _remove_stats_if_empty(channel_name: str, deleted_id: str) -> None:
        """
        Remove a channel's stats because no record contains the channel any more, unless
        a record was added to them in the meantime
        """

        log.debug("No records left with channel %s, removing stats", channel_name)
        await MongoDBInterface.delete_one(
            COLLECTION_NAME,
            {
                "_id": channel_name,
                "last_record_ids": {"$not": {"$elemMatch": {"$ne": deleted_id}}},
            },
        )

    @staticmethod
    async def _find_record_ids(
        channel_name: str,
        id_condition: Dict[str, str],
        direction: int,
        limit: int,
    ) -> List[str]:
        """
        Get the IDs of records containing a channel, whose ID meets `id_condition`
        (e.g. `{"$lt": some_id}`), nearest first in the direction given. Limiting the ID
        means the search starts there instead of at one end of the collection
        """

        records = MongoDBInterface.find(
            "records",
            filter_={
                "_id": id_condition,
                f"channels.{channel_name}": {"$exists": True},
            },
            limit=limit,
            sort=[("_id", direction)],
            projection=["_id"],
        )

        return [record["_id"] async for record in records]
