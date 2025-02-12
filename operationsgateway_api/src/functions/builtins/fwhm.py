from operationsgateway_api.src.functions.builtins.builtin import Builtin
from operationsgateway_api.src.functions.variable_models import WaveformVariable


class FWHM(Builtin):
    input_types = {"waveform"}
    output_type = "scalar"
    symbol = "fwhm"
    token = {
        "symbol": symbol,
        "name": "Full Width Half Maximum",
        "details": (
            "Calculate the FWHM of a waveform. Errors if image or scalar "
            "provided. Implementation: First, applies smoothing by taking weighted "
            "nearest and next-nearest neighbour contributions to  y values whose "
            "difference from their neighbours is more than 0.2 times the total "
            "range in y. "
            "The global maximum y value is then identified along with the first "
            "positions to either side of the peak where the y value is less than or "
            "equal to half the global maximum. If all y values to one side of the peak "
            "are greater than half the global maximum, the position of the global "
            "maximum is used. The difference between the values of x at these two "
            "positions is returned."
        ),
    }

    @staticmethod
    def evaluate(waveform: WaveformVariable) -> float:
        """
        Calculate the FWHM of a waveform. Errors if image or scalar provided.

        First, applies smoothing by taking weighted nearest and next-nearest
        neighbour contributions to  y values whose difference from their neighbours
        is more than 0.2 times the total range in y.

        The global maximum y value is then identified along with the first
        positions to either side of the peak where the y value is less than or
        equal to half the global maximum. If all y values to one side of the peak
        are greater than half the global maximum, the position of the global
        maximum is used. The difference between the values of x at these two
        positions is returned.
        """
        half_max_left, half_max_right = Builtin.calculate_fwhm(waveform)
        return half_max_right - half_max_left
