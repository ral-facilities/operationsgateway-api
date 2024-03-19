import numpy as np

from operationsgateway_api.src.functions.builtins.background import Background
from operationsgateway_api.src.functions.builtins.builtin import Builtin
from operationsgateway_api.src.functions.builtins.centre import Centre
from operationsgateway_api.src.functions.builtins.centroid_x import CentroidX
from operationsgateway_api.src.functions.builtins.centroid_y import CentroidY
from operationsgateway_api.src.functions.builtins.falling import Falling
from operationsgateway_api.src.functions.builtins.fwhm import FWHM
from operationsgateway_api.src.functions.builtins.fwhm_x import FWHMX
from operationsgateway_api.src.functions.builtins.fwhm_y import FWHMY
from operationsgateway_api.src.functions.builtins.integrate import Integrate
from operationsgateway_api.src.functions.builtins.rising import Rising
from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


class Builtins:
    builtins_dict: "dict[str, Builtin]" = {
        Background.symbol: Background,
        Centre.symbol: Centre,
        CentroidX.symbol: CentroidX,
        CentroidY.symbol: CentroidY,
        Falling.symbol: Falling,
        FWHM.symbol: FWHM,
        FWHMX.symbol: FWHMX,
        FWHMY.symbol: FWHMY,
        Integrate.symbol: Integrate,
        Rising.symbol: Rising,
    }
    tokens = [b.token for b in builtins_dict.values()]

    @staticmethod
    def get_builtin(builtin_name: str) -> Builtin:
        try:
            return Builtins.builtins_dict[builtin_name]
        except KeyError as e:
            raise AttributeError(
                f"'{builtin_name}' is not a recognised builtin function name",
            ) from e

    @staticmethod
    def type_check(tokens: list, is_evaluation: bool = False) -> str:
        builtin_name, argument = tokens
        builtin = Builtins.get_builtin(builtin_name)

        if is_evaluation:
            types_dict = {
                float: "scalar",
                WaveformVariable: "waveform",
                np.ndarray: "image",
            }
            argument = types_dict[type(argument)]

        if argument not in builtin.input_types:
            raise TypeError(
                f"'{builtin_name}' accepts {builtin.input_types} type(s), "
                f"'{argument}' provided",
            )

        return builtin.output_type

    @staticmethod
    def evaluate(tokens: list) -> str:
        Builtins.type_check(tokens, True)
        builtin_name, argument = tokens
        builtin = Builtins.get_builtin(builtin_name)
        return builtin.evaluate(argument)
