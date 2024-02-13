import numpy as np
import pytest

from operationsgateway_api.src.functions.builtins.centroid_x import CentroidX
from operationsgateway_api.src.functions.builtins.centroid_y import CentroidY


class TestCentroid:
    @pytest.mark.parametrize(
        "argument, expected_results",
        [
            pytest.param(np.ones((2, 2)), (0, 0), id="2 by 2"),
            pytest.param(np.ones((3, 3)), (1, 1), id="3 by 3"),
            pytest.param(np.ones((3, 1)), (0, 1), id="1 by 3"),
            pytest.param(
                np.array([[0, 0, 0, 0], [0, 1, 0, 0], [1, 2, 1, 0], [0, 1, 0, 0]]),
                (1, 2),
                id="4 by 4",
            ),
        ],
    )
    def test_centroid(
        self,
        argument: "list[int]",
        expected_results: "tuple[int, int]",
    ):
        x_result = CentroidX.evaluate(argument)
        y_result = CentroidY.evaluate(argument)

        assert np.isclose(x_result, expected_results[0])
        assert np.isclose(y_result, expected_results[1])
