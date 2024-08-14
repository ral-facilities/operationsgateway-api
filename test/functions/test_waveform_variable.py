import numpy as np
import pytest

from operationsgateway_api.src.functions import WaveformVariable


class TestWaveformVariable:
    @pytest.mark.parametrize(
        "expression, expected_result",
        [
            pytest.param(lambda x: x + 1, [2.0, 3.0, 4.0], id="__add__"),
            pytest.param(lambda x: 1 + x, [2.0, 3.0, 4.0], id="__radd__"),
            pytest.param(lambda x: x - 1, [0.0, 1.0, 2.0], id="__sub__"),
            pytest.param(lambda x: 1 - x, [0.0, -1.0, -2.0], id="__rsub__"),
            pytest.param(lambda x: x * 2, [2.0, 4.0, 6.0], id="__mul__"),
            pytest.param(lambda x: 2 * x, [2.0, 4.0, 6.0], id="__rmul__"),
            pytest.param(lambda x: x / 2, [0.5, 1.0, 1.5], id="__truediv__"),
            pytest.param(lambda x: 2 / x, [2.0, 1.0, 2 / 3], id="__rtruediv__"),
            pytest.param(lambda x: x**2, [1.0, 4.0, 9.0], id="__pow__"),
            pytest.param(lambda x: 2**x, [2.0, 4.0, 8.0], id="__rpow__"),
            pytest.param(lambda x: np.log(x), [0.0, 0.69314718, 1.09861229], id="log"),
            pytest.param(
                lambda x: np.exp(x),
                [2.71828183, 7.3890561, 20.08553692],
                id="exp",
            ),
        ],
    )
    def test_waveform_variable_element_wise(
        self,
        expression: callable,
        expected_result: "list[float]",
    ):
        array = np.array([1.0, 2.0, 3.0])
        waveform_variable = WaveformVariable(x=array.copy(), y=array.copy())
        result: WaveformVariable = expression(waveform_variable)

        assert np.allclose(result.x, [1, 2, 3])
        assert np.allclose(result.y, expected_result)

        string = f"y:\n{np.array(expected_result)}\nx:\n{array.copy()}"
        assert str(result) == string

    @pytest.mark.parametrize(
        "expression, expected_result",
        [
            pytest.param(lambda x: np.min(x), 1, id="min"),
            pytest.param(lambda x: np.mean(x), 2, id="mean"),
            pytest.param(lambda x: np.max(x), 3, id="max"),
        ],
    )
    def test_waveform_variable_reductive(
        self,
        expression: callable,
        expected_result: float,
    ):
        array = np.array([1.0, 2.0, 3.0])
        waveform_variable = WaveformVariable(x=array.copy(), y=array.copy())
        result: float = expression(waveform_variable)

        assert result == expected_result

    def test_waveform_variable_init_error(self):
        with pytest.raises(ValueError) as e:
            WaveformVariable()

        assert str(e.value) == "No arguments provided to __init__"
