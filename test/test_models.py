import numpy as np
import pytest

from operationsgateway_api.src.models import ImageChannelMetadataModel


class TestModels:
    @pytest.mark.parametrize(
        ["gain", "gain_type", "bit_depth", "bit_depth_type"],
        [
            pytest.param(1.0, float, 1, int, id="Python raw types"),
            pytest.param(np.float64(1), float, np.int64(1), int, id="Numpy dtypes"),
            pytest.param("1", str, "1", str, id="Castable strings"),
            pytest.param("one", str, "one", str, id="Un-castable strings"),
        ],
    )
    def test_image_channel_metadata_model(
        self,
        gain: "float | np.float64",
        gain_type: type,
        bit_depth: "int | np.int64",
        bit_depth_type: type,
    ):
        """
        Ensure that ints and floats are handled consistently by the __init__ of the
        model. Python dtypes should be case to raw types (to allow them to be dumped
        into Mongo) but even castable strings should not be accepted so we can raise a
        channel check error when the time comes.
        """
        model = ImageChannelMetadataModel(
            channel_dtype="image",
            gain=gain,
            bit_depth=bit_depth,
        )
        gain_correct = isinstance(model.gain, gain_type)
        bit_depth_correct = isinstance(model.bit_depth, bit_depth_type)
        assert gain_correct, f"{type(model.gain)} != {gain_type}"
        assert bit_depth_correct, f"{type(model.bit_depth)} != {bit_depth_type}"
