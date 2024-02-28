from typing import Literal

from lark import Transformer

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.functions.builtins.builtins import Builtins
from operationsgateway_api.src.functions.parser import parser


class TypeTransformer(Transformer):
    """Subclass of the Lark `Transformer` for determining the return type of an
    expression.

    The purpose of a Lark `Transformer` is to `transform` a `ParseTree` of
    `Token`s into some other format. To achieve this, callback functions defined
    on the class are called whenever a matching `Token` with that name is
    encountered in the `ParseTree`.

    For utility, the `evaluate` function accepts a `str` and performs the
    parsing under the hood.

    Attributes:
        function_types (dict):
            Map from name to return type for other functions that the expression
            being evaluated may depend on.
        channel_manifest (dict):
            Metadata for all known channels, including the data type.

    Examples:
        >>> type_transformer = TypeTransformer({"function_1": "image"})
        >>> type_transformer.evaluate("(channel_1 + function_1) / 2")
        'image'
    """

    def __init__(self, function_types: dict) -> None:
        """Initialises the Transformer and stores `function_types`.

        Args:
            function_types (dict):
                Map from name to return type for other functions that the
                expression being evaluated may depend on.
        """
        self.function_types = function_types
        super().__init__()

    async def evaluate(self, name: str, expression: str) -> str:
        """Parse and transform `expression` into the data type that the
        expression returns.

        Also fetches the most recent channel manifest asynchronously for
        lookups.

        Args:
            name (str): Name used to label the output of the `expression`.
            expression (str): Expression to be evaluated for return type.

        Raises:
            ValueError: If `name` is already a channel name.

        Returns:
            str: Return type of the function ("scalar", "waveform" or "image").
        """
        manifest = await ChannelManifest.get_most_recent_manifest()
        self.channel_manifest = manifest["channels"]

        if name in self.channel_manifest:
            raise ValueError(f"Function name '{name}' is already a channel name")

        tree = parser.parse(expression)
        return self.transform(tree)

    # Transformer callback functions

    # Values
    def constant(self, _) -> Literal["scalar"]:
        return "scalar"

    def variable(self, channel_name: list) -> str:
        name = "".join(channel_name)
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
    def builtin(self, tokens: list) -> str:
        return Builtins.type_check(tokens)

    def scalar_function(self, _) -> Literal["scalar"]:
        return "scalar"

    mean = scalar_function
    min = scalar_function  # noqa: A003
    max = scalar_function  # noqa: A003

    def element_wise_function(self, arguments: list) -> str:
        return arguments[0]

    log = element_wise_function
    exp = element_wise_function
