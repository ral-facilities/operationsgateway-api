from typing import Literal

from lark import Transformer

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.functions.builtins import (
    background_type_check,
    centre_type_check,
    centroid_x_type_check,
    centroid_y_type_check,
    falling_type_check,
    fwhm_type_check,
    fwhm_x_type_check,
    fwhm_y_type_check,
    integrate_type_check,
    rising_type_check,
)
from operationsgateway_api.src.functions.parser import parser


class TypeTransformer(Transformer):
    def __init__(self, function_types: dict, visit_tokens: bool = True) -> None:
        """
        Store `function_types` (return types for other functions) and initialise
        the Lark Transformer for evaluating return types.
        """
        self.function_types = function_types
        super().__init__(visit_tokens)

    async def evaluate(self, name: str, expression: str) -> str:
        """
        Parse `expression` and return the type that it will return.
        Types of channels are obtained from the channel manifest.
        """
        manifest = await ChannelManifest.get_most_recent_manifest()
        self.channel_manifest = manifest["channels"]

        if name in self.channel_manifest:
            raise ValueError(f"Function name '{name}' is already a channel name")

        tree = parser.parse(expression)
        return self.transform(tree)

    # Values
    def constant(self, _) -> Literal["scalar"]:
        return "scalar"

    def variable(self, name) -> str:
        (name,) = name
        if name in self.channel_manifest:
            return self.channel_manifest[name]["type"]
        elif name in self.function_types:
            return self.function_types[name]
        else:
            raise KeyError(f"'{name}' is not a recognised channel")

    # Operations
    def operation(self, operands) -> str:
        if operands[0] == operands[1] == "scalar":
            return "scalar"
        elif "image" in operands and "scalar" in operands:
            return "image"
        elif "waveform" in operands and "scalar" in operands:
            return "waveform"
        else:
            raise TypeError(f"Operation between types {operands} not supported")

    subtraction = operation
    addition = operation
    multiplication = operation
    division = operation
    exponentiation = operation

    # Functions
    def unknown(self, tokens: list) -> None:
        raise AttributeError(f"'{tokens[0]}' is not a recognised function name")

    def scalar_function(self, _) -> Literal["scalar"]:
        return "scalar"

    mean = scalar_function
    min = scalar_function  # noqa: A003
    max = scalar_function  # noqa: A003

    def element_wise_function(self, arguments: list) -> str:
        return arguments[0]

    log = element_wise_function
    exp = element_wise_function

    rising = rising_type_check
    falling = falling_type_check
    centre = centre_type_check
    fwhm = fwhm_type_check
    background = background_type_check
    integrate = integrate_type_check
    centroid_x = centroid_x_type_check
    centroid_y = centroid_y_type_check
    fwhm_x = fwhm_x_type_check
    fwhm_y = fwhm_y_type_check