import numpy as np

from operationsgateway_api.src.functions.builtins.builtin import Builtin
from operationsgateway_api.src.functions.builtins.centroid_x import CentroidX
from operationsgateway_api.src.functions.builtins.fwhm import FWHM
from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


class FWHMY(Builtin):
    input_types = {"image"}
    output_type = "scalar"
    symbol = "fwhm_y"
    token = {
        "symbol": symbol,
        "name": "Full Width Half Maximum (y)",
        "details": (
            "Calculate the FWHM of an image across the y axis, at the x position "
            "of the image centroid. Errors if waveform or scalar "
            "provided. Implementation: First, calculates the centroid and extracts "
            "the x position. Then applies smoothing by taking weighted "
            "nearest and next-nearest neighbour contributions to pixel values whose "
            "difference from their neighbours is more than 0.2 times the total "
            "range in values. The maximum value is then identified along with the "
            "positions bounding the FWHM and the distance in pixels returned."
        ),
    }

    @staticmethod
    def evaluate(image: np.ndarray) -> float:
        """
        First, calculates the centroid and extracts the x position. Then applies
        smoothing by taking weighted nearest and next-nearest neighbour
        contributions to pixel values whose difference from their neighbours is more
        than 0.2 times the total range in values. The maximum value is then
        identified along with the positions bounding the FWHM and the distance in
        pixels returned.
        """
        centroid_position = CentroidX.evaluate(image)
        y = image[:, centroid_position]
        waveform_variable = WaveformVariable(x=np.arange(len(y)), y=y)

        half_max_left, half_max_right = FWHM.calculate_fwhm(waveform_variable)
        return half_max_right - half_max_left
