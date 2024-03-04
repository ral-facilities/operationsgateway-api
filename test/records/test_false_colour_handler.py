import pytest

from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler


class TestFalseColourHandler:
    @pytest.mark.parametrize(
        "lower_level, vmin_expected",
        [
            pytest.param(
                None,
                {8: 0, 16: 0},
                id="None",
            ),
            pytest.param(
                0,
                {8: 0, 16: 0},
                id="0",
            ),
            pytest.param(
                1,
                {8: 1, 16: 256},
                id="1",
            ),
            pytest.param(
                64,
                {8: 64, 16: 64 * 256},
                id="64",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "upper_level, vmax_expected",
        [
            pytest.param(
                None,
                {8: 255, 16: 65535},
                id="None",
            ),
            pytest.param(
                255,
                {8: 255, 16: 65535},
                id="255",
            ),
            pytest.param(
                254,
                {8: 254, 16: 65535 - 256},
                id="256",
            ),
            pytest.param(
                191,
                {8: 191, 16: 192 * 256 - 1},
                id="191",
            ),
        ],
    )
    def test_pixel_limits(
        self,
        lower_level: int,
        vmin_expected: "dict[int, int]",
        upper_level: int,
        vmax_expected: "dict[int, int]",
    ):
        for bits_per_pixel in 8, 16:
            vmin, vmax = FalseColourHandler.pixel_limits(
                bits_per_pixel,
                lower_level,
                upper_level,
            )
            assert vmin == vmin_expected[bits_per_pixel]
            assert vmax == vmax_expected[bits_per_pixel]
