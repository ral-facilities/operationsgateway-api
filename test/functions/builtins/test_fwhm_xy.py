import numpy as np
import pytest

from operationsgateway_api.src.functions.builtins import (
    fwhm_x,
    fwhm_x_type_check,
    fwhm_y,
    fwhm_y_type_check,
)


class TestFWHMXY:
    @pytest.mark.parametrize(
        "argument, expected_results",
        [
            pytest.param(np.ones((2, 2)), (0, 0), id="2 by 2"),
            pytest.param(np.ones((3, 3)), (0, 0), id="3 by 3"),
            pytest.param(np.ones((3, 1)), (0, 0), id="1 by 3"),
            pytest.param(
                np.array([[0, 0, 0, 0], [0, 1, 0, 0], [1, 2, 1, 0], [0, 1, 0, 0]]),
                (2, 2),
                id="4 by 4",
            ),
        ],
    )
    def test_fwhm_xy(
        self,
        argument: list[int],
        expected_results: tuple[int, int],
    ):
        x_result = fwhm_x(None, [argument])
        y_result = fwhm_y(None, [argument])

        message = f"{x_result},{y_result} != {expected_results}"
        assert np.isclose(x_result, expected_results[0]), message
        assert np.isclose(y_result, expected_results[1]), message

    def test_fwhm_x_error(self):
        with pytest.raises(TypeError) as e:
            fwhm_x(None, [None])

        message = "'fwhm_x' accepts np.ndarray, <class 'NoneType'> provided"
        assert str(e.value) == message

    def test_fwhm_y_error(self):
        with pytest.raises(TypeError) as e:
            fwhm_y(None, [None])

        message = "'fwhm_y' accepts np.ndarray, <class 'NoneType'> provided"
        assert str(e.value) == message

    def test_fwhm_x_type_check_error(self):
        with pytest.raises(TypeError) as e:
            fwhm_x_type_check(None, ["scalar"])

        message = "'fwhm_x' accepts ['image'] type(s), 'scalar' provided"
        assert str(e.value) == message

    def test_fwhm_y_type_check_error(self):
        with pytest.raises(TypeError) as e:
            fwhm_y_type_check(None, ["scalar"])

        message = "'fwhm_y' accepts ['image'] type(s), 'scalar' provided"
        assert str(e.value) == message
