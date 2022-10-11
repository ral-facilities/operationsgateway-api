from typing import Union

from operationsgateway_api.src.models import Record as RecordModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.waveform import Waveform


class Record:
    def __init__(self, record: RecordModel) -> None:
        if isinstance(record, RecordModel):
            self.record = record
        elif isinstance(record, dict):
            # TODO - check there's exception handling around everytime a model is
            # created
            print(record.keys())
            self.record = RecordModel(**record)
        else:
            # TODO - should we be defensive and raise an exception?
            pass

    def store_thumbnail(self, data: Union[Image, Waveform]) -> None:
        if isinstance(data, Image):
            _, channel_name = data.extract_metadata_from_path()
        elif isinstance(data, Waveform):
            channel_name = data.get_channel_name_from_id()

        self.record.channels[channel_name].thumbnail = data.thumbnail

    async def insert(self):
        # TODO - exception handling
        await MongoDBInterface.insert_one(
            "records",
            self.record.dict(by_alias=True),
        )

    async def update(self):
        # This update query has been split into two one (which is iterated in a
        # loop) to add record metadata, and another to add each of the channels.
        # Based on some quick dev testing while making sure it worked, this doesn't
        # slow down ingestion times

        for metadata_key, value in self.record.metadata:
            await MongoDBInterface.update_one(
                "records",
                {"_id": self.record.id_},
                {"$set": {f"metadata.{metadata_key}": value}},
            )

        for channel_name, channel_value in self.record.channels.items():
            await MongoDBInterface.update_one(
                "records",
                {"_id": self.record.id_},
                {"$set": {f"channels.{channel_name}": channel_value.dict()}},
            )

    async def find_existing_record(self):
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
        return await MongoDBInterface.find_one(
            "records",
            {"_id": id_, **conditions},
        )

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
