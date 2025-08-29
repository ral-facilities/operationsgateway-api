import base64
from io import BytesIO

import imagehash
from PIL import Image as PILImage
import pytest

from operationsgateway_api.src.exceptions import FunctionParseError
from operationsgateway_api.src.models import PartialRecordModel
from operationsgateway_api.src.records.record_retriever import RecordRetriever


class TestRecordRetriever:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "channels",
        [
            pytest.param({}, id="No channels"),
            pytest.param(
                {
                    "TS-202-TSM-P1-CAM-2-CENX": {"data": 4.145480878063205},
                    "CM-202-CVC-SP": {
                        "waveform_path": "20230605100000/CM-202-CVC-SP.json",
                        "metadata": {"x_units": "nm"},
                    },
                    "FE-204-NSO-P1-CAM-1": {
                        "image_path": "20230605100000/FE-204-NSO-P1-CAM-1.png",
                    },
                },
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
        channels: dict[str, dict[str, float | str | dict[str, str]]],
        functions: "list[dict[str, str]]",
        values: "dict[str, dict]",
        clear_cached_echo_interface: None,
    ):
        # Use a copy to prevent in place modification of record.channels form persisting
        # between test executions
        record = PartialRecordModel(_id="20230605100000", channels=channels.copy())
        print(record.channels)
        record_retriever = RecordRetriever(
            record=record,
            functions=functions,
            original_image=False,
            colourmap_name="binary",
            return_thumbnails=True,
        )
        await record_retriever.process_functions()

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
        record_retriever = RecordRetriever(
            record,
            functions,
            False,
            colourmap_name="binary",
        )
        match = "{'b'} are not recognised channels/functions"
        with pytest.raises(FunctionParseError, match=match):
            await record_retriever.process_functions()

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
        record_retriever = RecordRetriever(
            record=record,
            functions=functions,
            original_image=False,
            colourmap_name="binary",
            return_thumbnails=True,
        )
        await record_retriever.process_functions()

        expected = {"data": 1, "metadata": {"channel_dtype": "scalar"}}
        assert record.channels is not None
        assert "a" not in record.channels  # Skip, TS-202-TSM-P1-CAM-2-CENX undefined
        assert "b" not in record.channels  # Skip, a undefined
        assert "c" in record.channels  # Has no dependencies, so should be returned
        assert record.channels["c"].model_dump(exclude_unset=True) == expected
