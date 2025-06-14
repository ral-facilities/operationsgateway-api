import base64
import copy
from io import BytesIO
from unittest.mock import patch

import imagehash
import numpy as np
from PIL import Image as PILImage
import pytest


from operationsgateway_api.src.exceptions import (
    FunctionParseError,
    MissingDocumentError,
    ModelError,
    RecordError,
)
from operationsgateway_api.src.models import (
    ImageModel,
    PartialRecordModel,
    RecordModel,
    WaveformModel,
)
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.records.waveform import Waveform


class TestRecord:
    test_record = {
        "_id": "19520605070023",
        "metadata": {
            "epac_ops_data_version": "1.0",
            "shotnum": 423648000000,
            "timestamp": "2023-06-05T08:00:00",
        },
        "channels": {
            "test-image-channel": {
                "metadata": {
                    "channel_dtype": "image",
                    "exposure_time_s": 0.0012,
                    "gain": 4.826012758558324,
                },
                "image_path": "19520605070023/test-image-channel.png",
                "thumbnail": b"iVBORw0KGgoAAAANSUhEUgAAAAMAAAADCAAAAABzQ+pjAAAAC0lEQVR4nGNgQAAAAAwAAXxMRMIAAAAASUVORK5CYII=",  # noqa: B950
            },
            "test-scalar-channel": {
                "metadata": {"channel_dtype": "scalar", "units": "µm"},
                "data": 5.126920467610521,
            },
            "test-waveform-channel": {
                "metadata": {"channel_dtype": "waveform", "x_units": "nm"},
                "thumbnail": b"iVBORw0KGgoAAAANSUhEUgAAAGQAAABLCAYAAACGGCK3AAAAOXRFWHRTb2Z0d2FyZQBNYXRwbG90bGliIHZlcnNpb24zLjcuNSwgaHR0cHM6Ly9tYXRwbG90bGliLm9yZy/xnp5ZAAAACXBIWXMAABP+AAAT/gEHlDmEAAAAx0lEQVR4nO3RQQ0AIBDAMMC/5+ONAvZoFSzZnplZZJzfAbwMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMiTEkxpAYQ2IMibkKGwSSalT8vgAAAABJRU5ErkJggg==",  # noqa: B950
                "waveform_path": "19520605070023/test-waveform-channel.json",
            },
        },
    }

    test_image = ImageModel(
        path="19520605070023/test-image-channel.png",
        data=np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint16),
    )

    test_waveform = WaveformModel(
        path="19520605070023/test-waveform-channel.json",
        x=[1.0],
        y=[8.0],
    )

    @pytest.mark.parametrize(
        "record_model, expected_exception, expected_raise_match",
        [
            pytest.param(
                "test string",
                RecordError,
                "RecordModel or dictionary not passed to Record init",
                id="RecordError",
            ),
            pytest.param(
                {"test": "validation error"},
                ModelError,
                "",
                id="ModelError",
            ),
        ],
    )
    def test_invalid_init(self, record_model, expected_exception, expected_raise_match):
        with pytest.raises(expected_exception, match=expected_raise_match):
            Record(record_model)

    @pytest.mark.parametrize(
        "waveform, channel_name",
        [
            pytest.param(
                True,
                "test-waveform-channel",
                id="Waveform thumbnail",
            ),
            pytest.param(
                False,
                "test-image-channel",
                id="Image thumbnail",
            ),
        ],
    )
    def test_store_thumbnail(self, waveform, channel_name):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        if waveform:
            data = Waveform(TestRecord.test_waveform)
        else:
            data = Image(TestRecord.test_image)

        test_bytes_thumbnail = base64.b64decode(
            TestRecord.test_record["channels"][channel_name]["thumbnail"],
        )
        test_img = PILImage.open(BytesIO(test_bytes_thumbnail))
        test_record_thumbnail_hash = str(imagehash.phash(test_img))

        data.create_thumbnail()
        record_instance.store_thumbnail(data)

        thumbnail = record_instance.record.channels[channel_name].thumbnail
        bytes_thumbnail = base64.b64decode(thumbnail)
        img = PILImage.open(BytesIO(bytes_thumbnail))
        thumbnail_hash = str(imagehash.phash(img))

        assert thumbnail_hash == test_record_thumbnail_hash

    def test_store_thumbnail_fail(self):
        record_model = RecordModel(**TestRecord.test_record)
        record_instance = Record(record_model)

        with pytest.raises(
            AttributeError,
            match="'str' object has no attribute 'get_channel_name_from_path'",
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

        duplicate_record["channels"]["test-scalar-channel"] = {
            "metadata": {"channel_dtype": "scalar", "units": "mV"},
            "data": 12.62848562,
        }

        new_record_model = RecordModel(**duplicate_record)
        new_record_instance = Record(new_record_model)
        await new_record_instance.update()

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
        record["channels"]["test-scalar-channel"]["metadata"][
            "channel_dtype"
        ] = "test_type"
        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.query_to_list",
            return_value=[record],
        ):
            recent_data = await Record.get_recent_channel_values(
                "test-scalar-channel",
                "colourmap_name",
                "float_colourmap",
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
        del record["channels"]["test-scalar-channel"]
        del record["channels"]["test-waveform-channel"]
        del record["channels"]["test-image-channel"]["thumbnail"]

        await record_instance.apply_false_colour_to_thumbnails(
            record=PartialRecordModel(**record),
            lower_level=2,
            upper_level=3,
            colourmap_name="test",
            float_colourmap_name="bwr",
            vector_skip=None,
            vector_limit=None,
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

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "record",
        [
            pytest.param(PartialRecordModel(_id="20230605100000"), id="No channels"),
            pytest.param(
                PartialRecordModel(
                    _id="20230605100000",
                    channels={
                        "TS-202-TSM-P1-CAM-2-CENX": {"data": 4.145480878063205},
                        "CM-202-CVC-SP": {
                            "waveform_path": "20230605100000/CM-202-CVC-SP.json",
                            "metadata": {"x_units": "nm"},
                        },
                        "FE-204-NSO-P1-CAM-1": {
                            "image_path": "20230605100000/FE-204-NSO-P1-CAM-1.png",
                        },
                    },
                ),
                id="Channels loaded",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "functions, values",
        [
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "TS-202-TSM-P1-CAM-2-CENX / 10",
                    },
                ],
                {
                    "a": {
                        "data": 0.4145480878063205,
                        "metadata": {"channel_dtype": "scalar"},
                    },
                },
                id="Scalar operation",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "TS-202-TSM-P1-CAM-2-CENX / 10",
                    },
                    {
                        "name": "b",
                        "expression": "log(a)",
                    },
                ],
                {
                    "a": {
                        "data": 0.4145480878063205,
                        "metadata": {"channel_dtype": "scalar"},
                    },
                    "b": {
                        "data": -0.880566297127881,
                        "metadata": {"channel_dtype": "scalar"},
                    },
                },
                id="Multiple functions",
            ),
            # Waveforms
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "CM-202-CVC-SP - 737.0041036717063",
                    },
                ],
                {
                    "a": {
                        "thumbnail": "bbb14eb0c14eb14e",
                        "metadata": {"channel_dtype": "waveform", "x_units": "nm"},
                    },
                },
                id="Waveform operation",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "log(CM-202-CVC-SP)",
                    },
                ],
                {
                    "a": {
                        "thumbnail": "ce39b1c74e6c9191",
                        "metadata": {"channel_dtype": "waveform", "x_units": "nm"},
                    },
                },
                id="Waveform element-wise function",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "mean(CM-202-CVC-SP)",
                    },
                ],
                {
                    "a": {
                        "data": 1721.4288093253808,
                        "metadata": {"channel_dtype": "scalar"},
                    },
                },
                id="Waveform reductive function",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "CM-202-CVC-SP - 737.0041036717063",
                    },
                    {
                        "name": "b",
                        "expression": "mean(a)",
                    },
                ],
                {
                    "a": {
                        "thumbnail": "bbb14eb0c14eb14e",
                        "metadata": {"channel_dtype": "waveform", "x_units": "nm"},
                    },
                    "b": {
                        "data": 984.4247056536747,
                        "metadata": {"channel_dtype": "scalar"},
                    },
                },
                id="Multiple waveform functions",
            ),
            # Images
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "FE-204-NSO-P1-CAM-1 - 1",
                    },
                ],
                {
                    "a": {
                        "thumbnail": "b9c0c6c9a79cccc5",
                        "metadata": {
                            "channel_dtype": "image",
                            "x_pixel_size": 1936,
                            "y_pixel_size": 1216,
                        },
                    },
                },
                id="Image operation",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "log(FE-204-NSO-P1-CAM-1)",
                    },
                ],
                {
                    "a": {
                        # Small pixel values appears as a "blank" image
                        "thumbnail": "8000000000000000",
                        "metadata": {
                            "channel_dtype": "image",
                            "x_pixel_size": 1936,
                            "y_pixel_size": 1216,
                        },
                    },
                },
                id="Image element-wise function",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "mean(FE-204-NSO-P1-CAM-1)",
                    },
                ],
                {
                    "a": {
                        "data": 376.9670147856405,
                        "metadata": {"channel_dtype": "scalar"},
                    },
                },
                id="Image reductive function",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "background(FE-204-NSO-P1-CAM-1)",
                    },
                ],
                {
                    "a": {
                        "data": 156.09,
                        "metadata": {"channel_dtype": "scalar"},
                    },
                },
                id="Image builtin function",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "FE-204-NSO-P1-CAM-1 - 1",
                    },
                    {
                        "name": "b",
                        "expression": "mean(a)",
                    },
                ],
                {
                    "a": {
                        "thumbnail": "b9c0c6c9a79cccc5",
                        "metadata": {
                            "channel_dtype": "image",
                            "x_pixel_size": 1936,
                            "y_pixel_size": 1216,
                        },
                    },
                    "b": {
                        "data": 375.9670147856405,
                        "metadata": {"channel_dtype": "scalar"},
                    },
                },
                id="Multiple image functions",
            ),
        ],
    )
    async def test_apply_functions(
        self,
        record: PartialRecordModel,
        functions: "list[dict[str, str]]",
        values: "dict[str, dict]",
    ):
        await Record.apply_functions(
            record=record,
            functions=functions,
            original_image=False,
            lower_level=0,
            upper_level=255,
            limit_bit_depth=8,
            colourmap_name="binary",
            return_thumbnails=True,
        )

        assert record.channels is not None
        for key, value in values.items():
            assert key in record.channels
            dump = record.channels[key].metadata.model_dump(exclude_unset=True)
            assert dump == value["metadata"]
            if "data" in value:
                assert record.channels[key].data == value["data"]
            else:
                image_b64 = record.channels[key].thumbnail
                image_bytes = base64.b64decode(image_b64)
                image = PILImage.open(BytesIO(image_bytes))
                image_phash = str(imagehash.phash(image))
                assert image_phash == value["thumbnail"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "functions",
        [
            [
                {
                    "name": "a",
                    "expression": "b / 10",
                },
                {
                    "name": "b",
                    "expression": "log(a)",
                },
            ],
        ],
    )
    async def test_apply_functions_failure(
        self,
        functions: "list[dict[str, str]]",
    ):
        record = PartialRecordModel(_id="20230605100000")
        with pytest.raises(FunctionParseError) as e:
            await Record.apply_functions(record, functions, False, 0, 255, 8, "binary")

        assert str(e.value) == "b is not known as a channel or function name"

    @pytest.mark.asyncio
    async def test_apply_functions_missing_channel(self):
        # Note we need a record where not all channels are defined, so not using
        # 20230605100000 as above
        record = PartialRecordModel(_id="20230604000000")
        functions = [
            {"name": "a", "expression": "TS-202-TSM-P1-CAM-2-CENX / 10"},
            {"name": "b", "expression": "a / 10"},
            {"name": "c", "expression": "1"},
        ]
        await Record.apply_functions(
            record=record,
            functions=functions,
            original_image=False,
            lower_level=0,
            upper_level=255,
            limit_bit_depth=8,
            colourmap_name="binary",
            return_thumbnails=True,
        )

        expected = {"data": 1, "metadata": {"channel_dtype": "scalar"}}
        assert record.channels is not None
        assert "a" not in record.channels  # Skip, TS-202-TSM-P1-CAM-2-CENX undefined
        assert "b" not in record.channels  # Skip, a undefined
        assert "c" in record.channels  # Has no dependencies, so should be returned
        assert record.channels["c"].model_dump(exclude_unset=True) == expected

    @pytest.mark.parametrize(
        ["img_array", "raw_bit_depth"],
        [
            pytest.param(np.ones(1, dtype=np.int32) * 4, 6),
            pytest.param(np.ones(1, dtype=np.int32) * 16, 12),
        ],
    )
    def test_bit_shift_to_raw(self, img_array: np.ndarray, raw_bit_depth: int):
        img = Record._bit_shift_to_raw(img_array=img_array, raw_bit_depth=raw_bit_depth)
        assert img[0] == 1

    @pytest.mark.parametrize(
        ["raw_bit_depth", "expected_value"],
        [
            pytest.param(6, 4, id="Expect upshift by 2 to 8 bit, 0001 -> 0100"),
            pytest.param(8, 1, id="Expect no shift as already 8 bit"),
            pytest.param(
                12,
                16,
                id="Expect upshift by 4 to 16 bit, 0000 0001 -> 0001 0000",
            ),
            pytest.param(16, 1, id="Expect no shift as already 16 bit"),
        ],
    )
    def test_bit_shift_to_storage(self, raw_bit_depth: int, expected_value: int):
        img = Record._bit_shift_to_storage(
            img_array=np.ones(1, dtype=np.int32),
            raw_bit_depth=raw_bit_depth,
        )
        assert img[0] == expected_value

    @pytest.mark.parametrize(
        ["truncate", "length"],
        [pytest.param(True, 50), pytest.param(False, 100)],
    )
    def test_truncate_bytes(self, truncate: bool, length: int):
        long_bytes = b"0" * 100
        truncated_bytes = Record.truncate_bytes(truncate=truncate, image_b64=long_bytes)
        assert len(truncated_bytes) == length
