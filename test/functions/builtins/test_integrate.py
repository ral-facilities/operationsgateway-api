import numpy as np
import pytest

from operationsgateway_api.src.functions import WaveformVariable
from operationsgateway_api.src.functions.builtins.integrate import Integrate


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
        argument: "WaveformVariable | np.ndarray",
        expected_result: float,
    ):
        result = Integrate.evaluate(argument)

        assert np.isclose(result, expected_result)

    def test_integrate_error(self):
        with pytest.raises(TypeError) as e:
            Integrate.evaluate(None)

        assert str(e.value) in (
            "'integrate' accepts {'image', 'waveform'} type(s), 'NoneType' provided",
            "'integrate' accepts {'waveform', 'image'} type(s), 'NoneType' provided",
        )
