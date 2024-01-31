import numpy as np
import pytest

from operationsgateway_api.src.functions import WaveformVariable
from operationsgateway_api.src.functions.builtins import integrate, integrate_type_check


class TestIntegrate:
    @pytest.mark.parametrize(
        "argument, expected_result",
        [
            pytest.param(WaveformVariable(x=np.arange(5), y=np.ones(5)), 4, id="Flat"),
            pytest.param(
                WaveformVariable(x=np.arange(5), y=np.arange(5)),
                20 / 3,
                id="Linear",
            ),
            pytest.param(
                WaveformVariable(x=np.arange(5), y=np.array([0, 1, 2, 1, 0])),
                34 / 9,
                id="Triangular",
            ),
            pytest.param(
                WaveformVariable(x=np.arange(5), y=np.array([0, 0, 0, 1, 0])),
                3 / 8,
                id="Delta",
            ),
            pytest.param(
                WaveformVariable(x=np.arange(5), y=np.array([1, 0, 3, 0, 1])),
                38 / 9,
                id="Noisy",
            ),
            pytest.param(
                WaveformVariable(x=np.arange(3), y=np.array([0, 1, 0])),
                3 / 7,
                id="Triple value",
            ),
            pytest.param(
                WaveformVariable(x=np.arange(2), y=np.array([0, 1])),
                0,
                id="Double value",
            ),
            pytest.param(
                WaveformVariable(x=np.arange(1), y=np.zeros(1)),
                0,
                id="Single value",
            ),
            pytest.param(np.ones((2, 2)), 4, id="Image"),
        ],
    )
    def test_integrate(
        self,
        argument: list[int],
        expected_result: int,
    ):
        result = integrate(None, [argument])

        assert np.isclose(result, expected_result)

    def test_integrate_error(self):
        with pytest.raises(TypeError) as e:
            integrate(None, [None])

        message = (
            "'integrate' accepts [WaveformVariable, np.ndarray], "
            "<class 'NoneType'> provided"
        )
        assert str(e.value) == message

    def test_integrate_type_check_error(self):
        with pytest.raises(TypeError) as e:
            integrate_type_check(None, ["scalar"])

        message = "'integrate' accepts ['waveform', 'image'] type(s), 'scalar' provided"
        assert str(e.value) == message
