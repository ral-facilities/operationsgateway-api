from operationsgateway_api.src.functions.builtins.builtin import Builtin
from operationsgateway_api.src.functions.variable_models import WaveformVariable


class Falling(Builtin):
    input_types = {"waveform"}
    output_type = "scalar"
    symbol = "falling"
    token = {
        "symbol": symbol,
        "name": "Falling",
        "details": (
            "Calculate the falling edge of a waveform. Errors if image or scalar "
            "provided. Implementation: First, applies smoothing by taking weighted "
            "nearest and next-nearest neighbour contributions to  y values whose "
            "difference from their neighbours is more than 0.2 times the total "
            "range in y. The global maximum y value is then identified along with the "
            "first x position to the right of the peak where the y value is less than "
            "or equal to half the global maximum. If all values of y to the right of "
            "the peak are greater than half the global maximum, the position of the "
            "global maximum is used. The value of x at this position is returned."
        ),
    }

    @staticmethod
    def evaluate(waveform: WaveformVariable) -> float:
        """
        Calculate the falling edge of a waveform. Errors if image or scalar provided.

        First, applies smoothing by taking weighted nearest and next-nearest
        neighbour contributions to  y values whose difference from their neighbours
        is more than 0.2 times the total range in y. The global maximum y value is then
        identified along with the first x position to the right of the peak where the y
        value is less than or equal to half the global maximum. If all values of y to
        the right of the peak are greater than half the global maximum, the position of
        the global maximum is used. The value of x at this position is returned."
        """
        _, half_max_right = Builtin.calculate_fwhm(waveform)
        return half_max_right
