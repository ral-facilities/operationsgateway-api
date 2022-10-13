import logging
from typing import Union

from pydantic import ValidationError

from operationsgateway_api.src.exceptions import (
    MissingDocumentError,
    ModelError,
    RecordError,
)
from operationsgateway_api.src.models import Record as RecordModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()


class Record:
    def __init__(self, record: RecordModel) -> None:
        if isinstance(record, RecordModel):
            self.record = record
        elif isinstance(record, dict):
            try:
                self.record = RecordModel(**record)
            except ValidationError as exc:
                raise ModelError(str(exc)) from exc
        else:
            raise RecordError("RecordModel or dictionary not passed to Record init")

    def store_thumbnail(self, data: Union[Image, Waveform]) -> None:
        if isinstance(data, Image):
            _, channel_name = data.extract_metadata_from_path()
        elif isinstance(data, Waveform):
            channel_name = data.get_channel_name_from_id()

        self.record.channels[channel_name].thumbnail = data.thumbnail

    async def insert(self):
        await MongoDBInterface.insert_one(
            "records",
            self.record.dict(by_alias=True, exclude_unset=True),
        )

    async def update(self):
        # This update query has been split into two one (which is iterated in a
        # loop) to add record metadata, and another to add each of the channels.
        # Based on some quick dev testing while making sure it worked, this doesn't
        # slow down ingestion times

        for metadata_key, value in self.record.metadata.dict(
            exclude_unset=True,
        ).items():
            await MongoDBInterface.update_one(
                "records",
                {"_id": self.record.id_},
                {"$set": {f"metadata.{metadata_key}": value}},
            )

        for channel_name, channel_value in self.record.channels.items():
            await MongoDBInterface.update_one(
                "records",
                {"_id": self.record.id_},
                {
                    "$set": {
                        f"channels.{channel_name}": channel_value.dict(
                            exclude_unset=True,
                        ),
                    },
                },
            )

    async def find_existing_record(self):
        log.debug(
            "Querying MongoDB to see if a record is already stored in the database",
        )
        record_dict = await MongoDBInterface.find_one(
            "records",
            filter_={"_id": self.record.id_},
        )

        if record_dict:
            existing_record = RecordModel(
                _id=record_dict["_id"],
                metadata=record_dict["metadata"],
                channels=record_dict["channels"],
            )
            return existing_record
        else:
            return None

    @staticmethod
    async def find_record(conditions, skip, limit, sort, projection):
        records_query = MongoDBInterface.find(
            collection_name="records",
            filter_=conditions,
            skip=skip,
            limit=limit,
            sort=sort,
            projection=projection,
        )
        records_data = await MongoDBInterface.query_to_list(records_query)
        return records_data

    @staticmethod
    async def find_record_by_id(id_, conditions):
        record_data = await MongoDBInterface.find_one(
            "records",
            {"_id": id_, **conditions},
        )

        if record_data:
            return record_data
        else:
            log.error("Record cannot be found. ID: %s, Conditions: %s", id_, conditions)
            raise MissingDocumentError("Record cannot be found")

    @staticmethod
    async def count_records(conditions):
        return await MongoDBInterface.count_documents("records", conditions)

    @staticmethod
    async def delete_record(id_):
        return await MongoDBInterface.delete_one("records", {"_id": id_})

    @staticmethod
    def truncate_thumbnails(record):
        for value in record["channels"].values():
            try:
                value["thumbnail"] = value["thumbnail"][:50]
            except KeyError:
                # If there's no thumbnails (e.g. if channel isn't an image or waveform)
                # then a KeyError will be raised. This is normal behaviour, so
                # acceptable to pass
                pass
