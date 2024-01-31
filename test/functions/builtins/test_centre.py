import numpy as np
import pytest

from operationsgateway_api.src.functions import WaveformVariable
from operationsgateway_api.src.functions.builtins import centre, centre_type_check


class TestCentre:
    @pytest.mark.parametrize(
        "y, expected_result",
        [
            pytest.param([1, 1, 1, 1, 1], 0, id="Flat"),
            pytest.param([0, 1, 2, 3, 4], 3, id="Linear"),
            pytest.param([0, 1, 2, 1, 0], 2, id="Triangular"),
            pytest.param([0, 0, 0, 1, 0], 3, id="Delta"),
            pytest.param([1, 0, 3, 0, 1], 2, id="Noisy"),
            pytest.param([0, 1, 0], 1, id="Triple value"),
            pytest.param([0, 1], 0.5, id="Double value"),
            pytest.param([0], 0, id="Single value"),
        ],
    )
    def test_centre(
        self,
        y: list[int],
        expected_result: int,
    ):
        waveform_variable = WaveformVariable(x=np.array([0, 1, 2, 3, 4]), y=np.array(y))
        result = centre(None, [waveform_variable])

        assert result == expected_result

    def test_centre_error(self):
        with pytest.raises(TypeError) as e:
            centre(None, [None])

        message = "'centre' accepts WaveformVariable, <class 'NoneType'> provided"
        assert str(e.value) == message

    def test_centre_type_check_error(self):
        with pytest.raises(TypeError) as e:
            centre_type_check(None, ["scalar"])

        message = "'centre' accepts ['waveform'] type(s), 'scalar' provided"
        assert str(e.value) == message
