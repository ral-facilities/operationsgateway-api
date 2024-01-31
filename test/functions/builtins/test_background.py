import numpy as np
import pytest

from operationsgateway_api.src.functions import WaveformVariable
from operationsgateway_api.src.functions.builtins import (
    background,
    background_type_check,
)


class TestBackground:
    @pytest.mark.parametrize(
        "argument, expected_result",
        [
            pytest.param(
                WaveformVariable(x=np.arange(1), y=np.zeros(1)),
                0,
                id="Short waveform",
            ),
            pytest.param(
                WaveformVariable(
                    x=np.arange(100),
                    y=np.concatenate((np.zeros(25), np.ones(50), np.zeros(25))),
                ),
                0,
                id="Long waveform",
            ),
            pytest.param(np.zeros((5, 5)), 0, id="Small image"),
            pytest.param(
                np.pad(np.zeros((5, 5)), (0, 15), "constant", constant_values=1),
                0.75,
                id="Big image",
            ),
        ],
    )
    def test_background(
        self,
        argument: WaveformVariable | np.ndarray,
        expected_result: int,
    ):
        result = background(None, [argument])

        assert result == expected_result

    def test_background_error(self):
        with pytest.raises(TypeError) as e:
            background(None, [None])

        message = (
            "'background' accepts [WaveformVariable, np.ndarray], "
            "<class 'NoneType'> provided"
        )
        assert str(e.value) == message

    def test_background_type_check_error(self):
        with pytest.raises(TypeError) as e:
            background_type_check(None, ["scalar"])

        message = (
            "'background' accepts ['waveform', 'image'] type(s), 'scalar' provided"
        )
        assert str(e.value) == message
