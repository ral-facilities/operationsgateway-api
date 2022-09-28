from operationsgateway_api.src.data_encoding import DataEncoding
from operationsgateway_api.src.models import Waveform as WaveformModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface


class Waveform:
    def __init__(self, waveform: WaveformModel) -> None:
        self.waveform = waveform
        # TODO - do we need to declare this here if it's just None?
        self.thumbnail = None
        self.is_stored = False

    async def is_waveform_stored(self) -> bool:
        waveform_exist = await MongoDBInterface.find_one(
            "waveforms", filter_={"_id": self.waveform.id_},
        )
        self.is_stored = True if waveform_exist else False

    async def insert_waveform(self):
        await self.is_waveform_stored()
        if not self.is_stored:
            # TODO - might have to convert self.waveform into dict/JSON?
            test = await MongoDBInterface.insert_one("waveforms", self.waveform)

    def create_thumbnail(self):
        # Think base64 conversion function will be elsewhere?
        pass

    @staticmethod
    async def get_waveform(waveform_id):
        return await MongoDBInterface.find_one(
            "waveforms",
            {"_id": waveform_id},
        )
