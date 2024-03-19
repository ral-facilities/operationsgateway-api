import base64
import io

import imagehash
from PIL import Image
import pytest

from operationsgateway_api.src.exceptions import FunctionParseError
from operationsgateway_api.src.records.record import Record


class TestRecord:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "record",
        [
            pytest.param({"_id": "20230605100000"}, id="No channels"),
            pytest.param(
                {
                    "_id": "20230605100000",
                    "channels": {
                        "TS-202-TSM-P1-CAM-2-CENX": {"data": 4.145480878063205},
                        "CM-202-CVC-SP": {
                            "waveform_path": "20230605100000/CM-202-CVC-SP.json",
                        },
                        "FE-204-NSO-P1-CAM-1": {
                            "image_path": "20230605100000/FE-204-NSO-P1-CAM-1.png",
                        },
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
            # Traces
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
                        "metadata": {"channel_dtype": "waveform"},
                    },
                },
                id="Trace operation",
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
                        "thumbnail": "ce39b1474e6c91a9",
                        "metadata": {"channel_dtype": "waveform"},
                    },
                },
                id="Trace element-wise function",
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
                id="Trace reductive function",
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
                        "thumbnail": "bac4c41eecc9cc69",
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
        ],
    )
    async def test_apply_functions(
        self,
        record: dict,
        functions: "list[dict[str, str]]",
        values: "dict[str, dict]",
    ):
        await Record.apply_functions(
            record,
            functions,
            0,
            255,
            "binary",
        )

        assert "channels" in record
        for key, value in values.items():
            assert key in record["channels"]
            assert "metadata" in record["channels"][key]
            assert record["channels"][key]["metadata"] == value["metadata"]
            if "data" in value:
                assert "data" in record["channels"][key]
                test_data = record["channels"][key]["data"]
                assert test_data == value["data"]
            else:
                assert "thumbnail" in record["channels"][key]
                image_b64 = record["channels"][key]["thumbnail"]
                image_bytes = base64.b64decode(image_b64)
                image = Image.open(io.BytesIO(image_bytes))
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
        record = {"_id": "20230605100000"}
        with pytest.raises(FunctionParseError) as e:
            await Record.apply_functions(record, functions, 0, 255, "binary")

        assert str(e.value) == "Unable to parse variables: {'b'}"
