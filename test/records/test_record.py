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
            pytest.param({"_id": "20220407141616"}, id="No channels"),
            pytest.param(
                {
                    "_id": "20220407141616",
                    "channels": {
                        "N_COMP_FF_YPOS": {"data": 235.734},
                        "N_COMP_SPEC_TRACE": {
                            "waveform_id": "20220407141616_N_COMP_SPEC_TRACE",
                        },
                        "N_COMP_FF_IMAGE": {
                            "image_path": "20220407141616/N_COMP_FF_IMAGE.png",
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
                        "expression": "N_COMP_FF_YPOS / 10",
                    },
                ],
                {"a": {"data": 23.5734, "metadata": {"channel_dtype": "scalar"}}},
                id="Scalar operation",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "N_COMP_FF_YPOS / 10",
                    },
                    {
                        "name": "b",
                        "expression": "log(a)",
                    },
                ],
                {
                    "a": {"data": 23.5734, "metadata": {"channel_dtype": "scalar"}},
                    "b": {
                        "data": 3.160118957711578,
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
                        "expression": "N_COMP_SPEC_TRACE - 737.0041036717063",
                    },
                ],
                {
                    "a": {
                        "thumbnail": "eee681193ac4dc69",
                        "metadata": {"channel_dtype": "waveform"},
                    },
                },
                id="Trace operation",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "log(N_COMP_SPEC_TRACE)",
                    },
                ],
                {
                    "a": {
                        "thumbnail": "eee681193ac0de69",
                        "metadata": {"channel_dtype": "waveform"},
                    },
                },
                id="Trace element-wise function",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "mean(N_COMP_SPEC_TRACE)",
                    },
                ],
                {
                    "a": {
                        "data": 737.0041036717063,
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
                        "expression": "N_COMP_FF_IMAGE - 4",
                    },
                ],
                {
                    "a": {
                        "thumbnail": "f3638c8c63739c8c",
                        "metadata": {
                            "channel_dtype": "image",
                            "x_pixel_size": 656,
                            "y_pixel_size": 494,
                        },
                    },
                },
                id="Image operation",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "log(N_COMP_FF_IMAGE)",
                    },
                ],
                {
                    "a": {
                        "thumbnail": "f3609c9963799cc4",
                        "metadata": {
                            "channel_dtype": "image",
                            "x_pixel_size": 656,
                            "y_pixel_size": 494,
                        },
                    },
                },
                id="Image element-wise function",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "mean(N_COMP_FF_IMAGE)",
                    },
                ],
                {
                    "a": {
                        "data": 6.841775081465389,
                        "metadata": {"channel_dtype": "scalar"},
                    },
                },
                id="Image reductive function",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "background(N_COMP_FF_IMAGE)",
                    },
                ],
                {
                    "a": {
                        "data": 3.77,
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
        functions: list,
        values: dict,
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
        functions,
    ):
        record = {"_id": "20220407141616"}
        with pytest.raises(FunctionParseError) as e:
            await Record.apply_functions(record, functions, 0, 255, "binary")

        assert str(e.value) == "Unable to parse variables: {'b'}"
