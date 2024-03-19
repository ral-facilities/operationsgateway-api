import numpy as np
import pytest

from operationsgateway_api.src.functions.builtins.fwhm_x import FWHMX
from operationsgateway_api.src.functions.builtins.fwhm_y import FWHMY


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
        argument: np.ndarray,
        expected_results: "tuple[int, int]",
    ):
        x_result = FWHMX.evaluate(argument)
        y_result = FWHMY.evaluate(argument)

        message = f"{x_result},{y_result} != {expected_results}"
        assert np.isclose(x_result, expected_results[0]), message
        assert np.isclose(y_result, expected_results[1]), message
