import base64
import copy
import datetime
from io import BytesIO
from unittest.mock import patch

import imagehash
import numpy as np
from PIL import Image as PILImage
import pytest

from operationsgateway_api.src.exceptions import (
    MissingDocumentError,
    ModelError,
    RecordError,
)
from operationsgateway_api.src.models import (
    ImageModel,
    RecordModel,
    WaveformModel,
)
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.records.waveform import Waveform


def convert_datetime(date_string):
    return datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")


class TestRecord:
    test_record = {
        "_id": "19520605070023",
        "metadata": {
            "epac_ops_data_version": "1.0",
            "shotnum": 423648000000,
            "timestamp": "2023-06-05T08:00:00",
        },
        "channels": {
            "test_image_id": {
                "metadata": {
                    "channel_dtype": "image",
                    "exposure_time_s": 0.0012,
                    "gain": 4.826012758558324,
                },
                "image_path": "19520605070023/test_image_id.png",
                "thumbnail": "0000000000000000",
            },
            "test_scalar_id": {
                "metadata": {"channel_dtype": "scalar", "units": "µm"},
                "data": 5.126920467610521,
            },
            "test_waveform_id": {
                "metadata": {"channel_dtype": "waveform", "x_units": "nm"},
                "thumbnail": "9291c43eb16b96ec",
                "waveform_id": "19520605070023_test_waveform_id",
            },
        },
    }

    test_image = ImageModel(
        path="19520605070023/test_image_id.png",
        data=np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint16),
    )

    test_waveform = WaveformModel(
        _id="19520605070023_test_waveform_id",
        x=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        y=[8.0, 3.0, 6.0, 2.0, 3.0, 8.0],
    )

    def test_init_record_error(self):
        record_model = "test string"

        with pytest.raises(
            RecordError,
            match="RecordModel or dictionary not passed to Record init",
        ):
            Record(record_model)

    def test_init_validation_error(self):
        record_model = {"test": "validation error"}

        with pytest.raises(ModelError, match=""):
            Record(record_model)

    def test_store_image_thumbnail(self):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        data = Image(TestRecord.test_image)
        data.create_thumbnail()
        record_instance.store_thumbnail(data)

        thumbnail = record_instance.record.channels["test_image_id"].thumbnail

        bytes_thumbnail = base64.b64decode(thumbnail)
        img = PILImage.open(BytesIO(bytes_thumbnail))
        thumbnail_checksum = str(imagehash.phash(img))

        assert (
            thumbnail_checksum
            == TestRecord.test_record["channels"]["test_image_id"]["thumbnail"]
        )

    def test_store_waveform_thumbnail(self):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        data = Waveform(TestRecord.test_waveform)
        data.create_thumbnail()
        record_instance.store_thumbnail(data)

        thumbnail = record_instance.record.channels["test_waveform_id"].thumbnail

        bytes_thumbnail = base64.b64decode(thumbnail)
        img = PILImage.open(BytesIO(bytes_thumbnail))
        thumbnail_checksum = str(imagehash.phash(img))

        assert (
            thumbnail_checksum
            == TestRecord.test_record["channels"]["test_waveform_id"]["thumbnail"]
        )

    def test_store_thumbnail_fail(self):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        with pytest.raises(
            AttributeError,
            match="'str' object has no attribute 'thumbnail",
        ):
            record_instance.store_thumbnail("test_image")

    @pytest.mark.asyncio
    async def test_insert_success(self, remove_record_entry):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        await record_instance.insert()

        record_result = await MongoDBInterface.find_one(
            "records",
            filter_={"_id": "19520605070023"},
        )

        assert record_result

    @pytest.mark.asyncio
    async def test_update_success(self, remove_record_entry):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        await record_instance.insert()

        duplicate_record = copy.deepcopy(TestRecord.test_record)

        duplicate_record["metadata"]["shotnum"] = 123456789
        duplicate_record["channels"]["test_scalar_id"] = {
            "metadata": {"channel_dtype": "scalar", "units": "edty"},
            "data": 5.126920467610521,
        }

        new_record_model = RecordModel(**duplicate_record)
        new_record_instance = Record(new_record_model)

        await new_record_instance.update()

        duplicate_record["metadata"]["timestamp"] = convert_datetime(
            duplicate_record["metadata"]["timestamp"],
        )

        record_result = await MongoDBInterface.find_one(
            "records",
            filter_={"_id": "19520605070023"},
        )

        assert record_result == duplicate_record

    @pytest.mark.asyncio
    async def test_find_record(self, remove_record_entry):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        result_none = await record_instance.find_existing_record()

        assert result_none is None

        await record_instance.insert()

        result_record = await record_instance.find_existing_record()

        assert result_record == RecordModel(**TestRecord.test_record)

    @pytest.mark.asyncio
    async def test_record_not_found(self):
        with pytest.raises(MissingDocumentError, match="Record cannot be found"):
            record_dict = await Record.find_record_by_id(
                "19520605070023",
                {},
            )
            assert record_dict is None

    @pytest.mark.asyncio
    async def test_incorrect_channel_dtype(self):
        record = TestRecord.test_record
        record["channels"]["test_scalar_id"]["metadata"]["channel_dtype"] = "test_type"
        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.query_to_list",
            return_value=[record],
        ):
            recent_data = await Record.get_recent_channel_values(
                "test_scalar_id",
                "colourmap_name",
            )
            assert recent_data == []

    @pytest.mark.asyncio
    async def test_delete_record(self):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        await record_instance.insert()

        await record_instance.delete_record("19520605070023")

        result_none = await record_instance.find_existing_record()

        assert result_none is None

    @pytest.mark.asyncio
    async def test_ignore_scalar_thumbnail(self):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        record = TestRecord.test_record
        del record["channels"]["test_scalar_id"]
        del record["channels"]["test_waveform_id"]
        del record["channels"]["test_image_id"]["thumbnail"]

        await record_instance.apply_false_colour_to_thumbnails(
            record=record,
            lower_level=2,
            upper_level=3,
            colourmap_name="test",
        )

    @pytest.mark.asyncio
    async def test_convert_search_none_range(self):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        with pytest.raises(
            RecordError,
            match="Both date range and shot number range are None",
        ):
            await record_instance.convert_search_ranges(
                date_range=None,
                shotnum_range=None,
            )

    @pytest.mark.asyncio
    async def test_convert_search_range_validation_error(self):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.aggregate",
            return_value=[{"key1": "test_val_1", "key2": "test_val_2"}],
        ):
            with pytest.raises(ModelError):
                await record_instance.convert_search_ranges(
                    date_range={
                        "from": "2022-04-07 14:16:19",
                        "to": "2022-04-07 21:00:00",
                    },
                    shotnum_range=None,
                )
