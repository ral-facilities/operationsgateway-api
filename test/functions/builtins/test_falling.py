import numpy as np
import pytest

from operationsgateway_api.src.functions import WaveformVariable
from operationsgateway_api.src.functions.builtins.falling import Falling


class TestFalling:
    @pytest.mark.parametrize(
        "y, expected_result",
        [
            pytest.param([1, 1, 1, 1, 1], 0, id="Flat"),
            pytest.param([0, 1, 2, 3, 4], 4, id="Linear"),
            pytest.param([0, 1, 2, 1, 0], 4, id="Triangular"),
            pytest.param([0, 0, 0, 1, 0], 4, id="Delta"),
            pytest.param([1, 0, 3, 0, 1], 3, id="Noisy"),
            pytest.param([0, 1, 0], 2, id="Triple value"),
            pytest.param([0, 1], 1, id="Double value"),
            pytest.param([0], 0, id="Single value"),
        ],
    )
    def test_falling(
        self,
        y: "list[int]",
        expected_result: int,
    ):
        waveform_variable = WaveformVariable(x=np.array([0, 1, 2, 3, 4]), y=np.array(y))
        result = Falling.evaluate(waveform_variable)

        assert result == expected_result
