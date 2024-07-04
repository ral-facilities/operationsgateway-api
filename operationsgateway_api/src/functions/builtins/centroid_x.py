import numpy as np

from operationsgateway_api.src.functions.builtins.builtin import Builtin


class CentroidX(Builtin):
    input_types = {"image"}
    output_type = "scalar"
    symbol = "centroid_x"
    token = {
        "symbol": symbol,
        "name": "Centroid (x)",
        "details": (
            "Calculate the x position of the centroid of an image. Errors if "
            "waveform or scalar provided. Implementation: Returns the x position "
            "of the image's centroid in terms of pixel values."
        ),
    }

    @staticmethod
    def evaluate(image: np.ndarray) -> float:
        """
        Returns the x position of the image's centroid in terms of pixel values.
        """
        return Builtin.centroid(image, 0)