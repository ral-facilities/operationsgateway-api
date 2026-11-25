from collections.abc import Iterable
import logging
from typing import Any

import pymongo

from operationsgateway_api.src.exceptions import DatabaseError
from operationsgateway_api.src.models import ChannelStatsModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface

log = logging.getLogger()

COLLECTION_NAME = "channel_stats"
NUM_RECENT_RECORDS = 3


def _recent_ids() -> dict[str, list[str | list[str]]]:
    """The channel's current newest record IDs, or none if it has no stats yet"""
    return {"$ifNull": ["$last_record_ids", []]}


def _earlier_of(first_record_id: str, record_id: str) -> dict[str, list[str]]:
    """The earlier ID of the two. A missing first ID is ignored, so a channel's first
    record becomes its first ID"""
    return {"$min": [first_record_id, record_id]}


def _with_ids(record_ids: Any, extra_ids: Any) -> dict:
    """`record_ids` and `extra_ids` together, without duplicates"""
    return {"$setUnion": [record_ids, extra_ids]}


def _without_id(record_ids: Any, record_id: str) -> dict:
    """`record_ids` with `record_id` taken out"""
    return {"$setDifference": [record_ids, [record_id]]}


def _newest(record_ids: Any) -> dict:
    """The newest `NUM_RECENT_RECORDS` of `record_ids`, newest first"""
    return {
        "$slice": [
            {"$sortArray": {"input": record_ids, "sortBy": -1}},
            NUM_RECENT_RECORDS,
        ],
    }


def _replace_id(field: str, old_id: str, new_id: str) -> dict:
    """The value of `field`, with `new_id` in its place if it's `old_id`"""
    return {"$cond": [{"$eq": [field, old_id]}, new_id, field]}


class ChannelStats:
    """
    Keeps track of the first and most recent records that contain each channel, stored
    as one document per channel (the `_id` being the channel name)
    """

    @staticmethod
    def update_pipeline(record_id: str) -> list[dict[str, Any]]:
        """
        Build the update which adds a record to a channel's stats.

        It sets the channel's:
        - first record to the earlier of its current first record and this one. That
          can move it earlier, if an old record is ingested after newer ones
        - newest records to the current newest plus this one, keeping the newest three.
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

        Each channel is a separate update for now.
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
        Updates the stats of every channel in a record that has just been stored,
        The record is already saved at this point.
        If this fails it logs a failure instead of raising it
        """

        try:
            await ChannelStats.update_for_record(record_id, channel_names)
        except DatabaseError:
            log.exception("Failed to update channel stats for record %s", record_id)

    @staticmethod
    async def get(channel_name: str) -> ChannelStatsModel | None:
        """
        Get a channel's stats, or `None` if the channel has no stats (which means no
        stored record contains it)
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
        been deleted.

        The record must be deleted first, or it could be chosen as its own replacement.
        A channel stops referring to the record once it has been corrected, so if this
        fails part way through, running it again finishes the remaining channels.
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
        """

        channel_name = stats.id_
        # Get the remaining ids that aren't the deleted record. The deleted record may
        # not be listed at all, if it was only the channel's first record
        remaining_ids = [id_ for id_ in stats.last_record_ids if id_ != record_id]

        # With fewer than `NUM_RECENT_RECORDS` listed on `stats` before the deletion,
        # every record with the channel is listed, so there are no other records to
        # search for
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
        remaining_ids: list[str],
    ) -> list[str]:
        """
        Find the records which fill the places in a channel's newest records left by a
        deleted one.
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
        remaining_ids: list[str],
        list_is_complete: bool,
    ) -> str | None:
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
        Remove a channel's stats because no record contains the channel any more
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
        id_condition: dict[str, str],
        direction: int,
        limit: int,
    ) -> list[str]:
        """
        Get the IDs of records containing a channel, whose ID meets `id_condition`
        (e.g. `{"$lt": some_id}`), nearest first in the direction given.
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
