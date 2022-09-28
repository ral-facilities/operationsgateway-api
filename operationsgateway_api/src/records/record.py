from typing import Union
from operationsgateway_api.src.models import RecordM as RecordModel
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.waveform import Waveform

class Record:
    def __init__(self, record: RecordModel) -> None:
        self.record = record
        self.is_stored = False
    
    def store_thumbnail(self, data: Union[Image, Waveform]) -> None:
        if isinstance(data, Image):
            _, channel_name = data.extract_metadata_from_path()
        elif isinstance(data, Waveform):
            channel_name = data.get_channel_name_from_id()

        self.record.channels[channel_name].thumbnail = data.thumbnail
