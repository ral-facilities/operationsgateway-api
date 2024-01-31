import numpy as np
import pytest

from operationsgateway_api.src.functions.builtins import (
    centroid_x,
    centroid_x_type_check,
    centroid_y,
    centroid_y_type_check,
)


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
        argument: list[int],
        expected_results: tuple[int, int],
    ):
        x_result = centroid_x(None, [argument])
        y_result = centroid_y(None, [argument])

        assert np.isclose(x_result, expected_results[0])
        assert np.isclose(y_result, expected_results[1])

    def test_centroid_x_error(self):
        with pytest.raises(TypeError) as e:
            centroid_x(None, [None])

        message = "'centroid_x' accepts np.ndarray, <class 'NoneType'> provided"
        assert str(e.value) == message

    def test_centroid_y_error(self):
        with pytest.raises(TypeError) as e:
            centroid_y(None, [None])

        message = "'centroid_y' accepts np.ndarray, <class 'NoneType'> provided"
        assert str(e.value) == message

    def test_centroid_x_type_check_error(self):
        with pytest.raises(TypeError) as e:
            centroid_x_type_check(None, ["scalar"])

        message = "'centroid_x' accepts ['image'] type(s), 'scalar' provided"
        assert str(e.value) == message

    def test_centroid_y_type_check_error(self):
        with pytest.raises(TypeError) as e:
            centroid_y_type_check(None, ["scalar"])

        message = "'centroid_y' accepts ['image'] type(s), 'scalar' provided"
        assert str(e.value) == message
