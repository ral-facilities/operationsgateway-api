import copy
import datetime
from unittest.mock import patch

import numpy as np
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
                "thumbnail": "iVBORw0KGgoAAAANSUhEUgAAAAMAAAADCAAAAABzQ+pjAAAAC0lE"
                "QVR4nGNgQAAAAAwAAXxMRMIAAAAASUVORK5CYII=",
            },
            "test_scalar_id": {
                "metadata": {"channel_dtype": "scalar", "units": "µm"},
                "data": 5.126920467610521,
            },
            "test_waveform_id": {
                "metadata": {"channel_dtype": "waveform", "x_units": "nm"},
                "thumbnail": "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",  # noqa: B950
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

        assert (record_instance.record.channels["test_image_id"].thumbnail).decode(
            "utf-8",
        ) == TestRecord.test_record["channels"]["test_image_id"]["thumbnail"]

    def test_store_waveform_thumbnail(self):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        data = Waveform(TestRecord.test_waveform)
        data.create_thumbnail()
        record_instance.store_thumbnail(data)

        assert (record_instance.record.channels["test_waveform_id"].thumbnail).decode(
            "utf-8",
        ) == TestRecord.test_record["channels"]["test_waveform_id"]["thumbnail"]

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
