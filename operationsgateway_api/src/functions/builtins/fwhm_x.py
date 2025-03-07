import numpy as np

from operationsgateway_api.src.functions.builtins.builtin import Builtin
from operationsgateway_api.src.functions.builtins.centroid_y import CentroidY
from operationsgateway_api.src.functions.builtins.fwhm import FWHM
from operationsgateway_api.src.functions.variable_models import WaveformVariable


class FWHMX(Builtin):
    input_types = {"image"}
    output_type = "scalar"
    symbol = "fwhm_x"
    token = {
        "symbol": symbol,
        "name": "Full Width Half Maximum (x)",
        "details": (
            "Calculate the FWHM of an image across the x axis, at the y position "
            "of the image centroid. Errors if waveform or scalar "
            "provided. Implementation: First, calculates the centroid and extracts "
            "the y position. Then applies smoothing by taking weighted "
            "nearest and next-nearest neighbour contributions to pixel values whose "
            "difference from their neighbours is more than 0.2 times the total "
            "range in values. "
            "The global maximum value is then identified along with the first "
            "positions to either side of the peak where the pixel value is less than "
            "or equal to half the global maximum. If all pixel values to one side of "
            "the peak are greater than half the global maximum, the position of the "
            "global maximum is used. The difference between these two positions in "
            "number of pixels is returned."
        ),
    }

    @staticmethod
    def evaluate(image: np.ndarray) -> float:
        """
        Calculate the FWHM of an image across the x axis, at the y position of the image
        centroid. Errors if waveform or scalar provided.

        First, calculates the centroid and extracts the row at that position. Then
        applies smoothing by taking weighted nearest and next-nearest neighbour
        contributions to pixel values whose difference from their neighbours is more
        than 0.2 times the total range in values.

        The global maximum value is then identified along with the first
        positions to either side of the peak where the pixel value is less than
        or equal to half the global maximum. If all pixel values to one side of
        the peak are greater than half the global maximum, the position of the
        global maximum is used. The difference between these two positions in
        number of pixels is returned.
        """
        centroid_position = CentroidY.evaluate(image)
        y = image[centroid_position]
        waveform_variable = WaveformVariable(x=np.arange(len(y)), y=y)

        half_max_left, half_max_right = FWHM.calculate_fwhm(waveform_variable)
        return half_max_right - half_max_left
