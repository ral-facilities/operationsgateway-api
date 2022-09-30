from typing import Union
from operationsgateway_api.src.models import RecordM as RecordModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.waveform import Waveform

class Record:
    def __init__(self, record: RecordModel) -> None:
        self.record = record
        # TODO - is this needed?
        self.is_stored = False
    
    def store_thumbnail(self, data: Union[Image, Waveform]) -> None:
        if isinstance(data, Image):
            _, channel_name = data.extract_metadata_from_path()
        elif isinstance(data, Waveform):
            channel_name = data.get_channel_name_from_id()

        self.record.channels[channel_name].thumbnail = data.thumbnail

    async def insert(self):
        # TODO - exception handling
        await MongoDBInterface.insert_one(
            "records", self.record.dict(by_alias=True),
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
            "records", filter_={"_id": self.record.id_},
        )

        if record_dict:
            existing_record = RecordModel(
                _id=record_dict["_id"],
                metadata=record_dict["metadata"],
                channels=record_dict["channels"]
            )
            return existing_record
        else:
            return None
