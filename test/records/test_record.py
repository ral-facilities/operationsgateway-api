import numpy as np
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
        "functions, all_variables, values",
        [
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "N_COMP_FF_YPOS / 10",
                        "variables": ["N_COMP_FF_YPOS"],
                    },
                ],
                {"N_COMP_FF_YPOS"},
                {"a": {"data": 23.5734, "metadata": {"channel_dtype": "scalar"}}},
                id="Scalar operation",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "N_COMP_FF_YPOS / 10",
                        "variables": ["N_COMP_FF_YPOS"],
                    },
                    {
                        "name": "b",
                        "expression": "log(a)",
                        "variables": [],
                    },
                ],
                {"N_COMP_FF_YPOS"},
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
                        "variables": ["N_COMP_SPEC_TRACE"],
                    },
                ],
                {"N_COMP_SPEC_TRACE"},
                {
                    "a": {
                        "data": [
                            -24.004103671706275,
                            10.995896328293725,
                            41.995896328293725,
                        ],
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
                        "variables": ["N_COMP_SPEC_TRACE"],
                    },
                ],
                {"N_COMP_SPEC_TRACE"},
                {
                    "a": {
                        "data": [
                            6.569481420414296,
                            6.617402977974478,
                            6.658011045870748,
                        ],
                        "metadata": {"channel_dtype": "waveform"},
                    },
                },
                id="Trace element-wise function",
            ),
            pytest.param(
                [
                    {
                        "name": "a",
                        "expression": "avg(N_COMP_SPEC_TRACE)",
                        "variables": ["N_COMP_SPEC_TRACE"],
                    },
                ],
                {"N_COMP_SPEC_TRACE"},
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
                        "variables": ["N_COMP_FF_IMAGE"],
                    },
                ],
                {"N_COMP_FF_IMAGE"},
                {
                    "a": {
                        "data": [-1, 1, -2],
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
                        "variables": ["N_COMP_FF_IMAGE"],
                    },
                ],
                {"N_COMP_FF_IMAGE"},
                {
                    "a": {
                        "data": [1.09861229, 1.60943791, 0.69314718],
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
                        "expression": "avg(N_COMP_FF_IMAGE)",
                        "variables": ["N_COMP_FF_IMAGE"],
                    },
                ],
                {"N_COMP_FF_IMAGE"},
                {
                    "a": {
                        "data": 6.841775081465389,
                        "metadata": {"channel_dtype": "scalar"},
                    },
                },
                id="Image reductive function",
            ),
        ],
    )
    async def test_apply_functions(
        self,
        record,
        functions,
        all_variables,
        values,
    ):
        await Record.apply_functions(
            record,
            functions,
            all_variables.copy(),
            0,
            255,
            "binary",
        )

        assert "channels" in record
        for key, value in values.items():
            assert key in record["channels"]
            assert "metadata" in record["channels"][key]
            assert record["channels"][key]["metadata"] == value["metadata"]
            assert "data" in record["channels"][key]
            expected_data = value["data"]
            test_data = record["channels"][key]["data"]
            if isinstance(expected_data, float):
                assert test_data == value["data"]
            else:
                # Only assert on first few entries for convenience
                if isinstance(test_data[0], list):
                    test_data = test_data[0]
                test_data_slice = test_data[: len(expected_data)]
                message = f"{test_data_slice} == {expected_data}"
                assert np.allclose(test_data_slice, expected_data), message
                assert "thumbnail" in record["channels"][key]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "functions",
        [
            [
                {
                    "name": "a",
                    "expression": "b / 10",
                    "variables": [],
                },
                {
                    "name": "b",
                    "expression": "log(a)",
                    "variables": [],
                },
            ],
        ],
    )
    async def test_apply_functions_failure(
        self,
        functions,
    ):
        with pytest.raises(FunctionParseError) as e:
            await Record.apply_functions({}, functions, {}, 0, 255, "binary")

        assert str(e.value) == "ERR200 - Failed to create variable: 'b'Symbol Error"
