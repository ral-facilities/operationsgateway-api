import numpy as np
import pytest

from operationsgateway_api.src.functions import WaveformVariable
from operationsgateway_api.src.functions.builtins import rising, rising_type_check


class TestRising:
    @pytest.mark.parametrize(
        "y, expected_result",
        [
            pytest.param([1, 1, 1, 1, 1], 0, id="Flat"),
            pytest.param([0, 1, 2, 3, 4], 2, id="Linear"),
            pytest.param([0, 1, 2, 1, 0], 0, id="Triangular"),
            pytest.param([0, 0, 0, 1, 0], 2, id="Delta"),
            pytest.param([1, 0, 3, 0, 1], 1, id="Noisy"),
            pytest.param([0, 1, 0], 0, id="Triple value"),
            pytest.param([0, 1], 0, id="Double value"),
            pytest.param([0], 0, id="Single value"),
        ],
    )
    def test_rising(
        self,
        y: list[int],
        expected_result: int,
    ):
        waveform_variable = WaveformVariable(x=np.array([0, 1, 2, 3, 4]), y=np.array(y))
        result = rising(None, [waveform_variable])

        assert result == expected_result

    def test_rising_error(self):
        with pytest.raises(TypeError) as e:
            rising(None, [None])

        message = "'rising' accepts WaveformVariable, <class 'NoneType'> provided"
        assert str(e.value) == message

    def test_rising_type_check_error(self):
        with pytest.raises(TypeError) as e:
            rising_type_check(None, ["scalar"])

        message = "'rising' accepts ['waveform'] type(s), 'scalar' provided"
        assert str(e.value) == message
