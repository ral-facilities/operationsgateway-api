import numpy as np
from pydantic import ValidationError
import pytest

from operationsgateway_api.src.exceptions import ChannelManifestError
from operationsgateway_api.src.models import (
    ChannelDtype,
    ChannelModel,
    ImageChannelMetadataModel,
)


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

    @pytest.mark.parametrize(
        ["metadata", "expected"],
        [
            pytest.param(
                {"x_units": "J"},
                "Only waveform channels should contain waveform channel metadata.",
            ),
            pytest.param(
                {"y_units": "J"},
                "Only waveform channels should contain waveform channel metadata.",
            ),
            pytest.param(
                {"labels": ["Tilt X", "Tilt Y"]},
                "Only vector channels should contain vector channel metadata.",
            ),
        ],
    )
    def test_channel_model(self, metadata: dict, expected: str):
        with pytest.raises(ChannelManifestError) as e:
            ChannelModel(name="name", path="path", type=ChannelDtype.SCALAR, **metadata)

        assert e.exconly() == (
            f"operationsgateway_api.src.exceptions.ChannelManifestError: {expected} "
            "Invalid channel is called: name"
        )
