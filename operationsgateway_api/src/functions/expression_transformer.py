from lark import Transformer
import numpy as np

from operationsgateway_api.src.functions.builtins.builtins import Builtins
from operationsgateway_api.src.functions.parser import parser
from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


class ExpressionTransformer(Transformer):
    """Subclass of the Lark `Transformer` for evaluating an expression to return
    a numerical result.

    The purpose of a Lark `Transformer` is to `transform` a `ParseTree` of
    `Token`s into some other format. To achieve this, callback functions defined
    on the class are called whenever a matching `Token` with that name is
    encountered in the `ParseTree`.

    For utility, the `evaluate` function accepts a `str` and performs the
    parsing under the hood.

    Attributes:
        channels (dict):
            Mapping of channel or other function names to their numerical value
            (for a given record, upon which we are evaluating).

    Examples:
        >>> expression_transformer = ExpressionTransformer(
            {"function_1": np.ones((2, 2)), "channel_1": 10}
        )
        >>> expression_transformer.evaluate("(channel_1 + function_1) / 2")
        array([[5.5, 5.5],
               [5.5, 5.5]])
    """

    def __init__(self, channels: dict) -> None:
        """Initialises the Transformer and stores `channels`.

        Args:
            channels (dict):
                Map from name to numerical value for channels and other
                functions that the expression being evaluated depends on.
        """
        self.channels = channels
        super().__init__()

    def evaluate(self, expression: str) -> "np.ndarray | WaveformVariable | float":
        """Parse and transform `expression` into the numerical value for this
        record.

        Args:
            expression (str): Expression to be numerically evaluated.

        Returns:
            np.ndarray | WaveformVariable | float:
                Numeric value for this expression and record.
        """
        tree = parser.parse(expression)
        return self.transform(tree)

    # Transformer callback functions

    # Values
    def constant(self, number) -> float:
        (number,) = number
        return float(number)

    def variable(self, channel_name) -> "np.ndarray | WaveformVariable | float":
        return self.channels["".join(channel_name)]

    # Operations
    def subtraction(self, operands) -> "np.ndarray | WaveformVariable | float":
        return operands[0] - operands[1]

    def addition(self, operands) -> "np.ndarray | WaveformVariable | float":
        return operands[0] + operands[1]

    def multiplication(self, operands) -> "np.ndarray | WaveformVariable | float":
        return operands[0] * operands[1]

    def division(self, operands) -> "np.ndarray | WaveformVariable | float":
        return operands[0] / operands[1]

    def exponentiation(self, operands) -> "np.ndarray | WaveformVariable | float":
        return operands[0] ** operands[1]

    # Functions
    def builtin(self, tokens) -> "np.ndarray | WaveformVariable | float":
        return Builtins.evaluate(tokens)

    def mean(self, arguments) -> float:
        return np.mean(arguments[0])

    def min(self, arguments) -> float:  # noqa: A003
        return np.min(arguments[0])

    def max(self, arguments) -> float:  # noqa: A003
        return np.max(arguments[0])

    def log(self, arguments) -> "np.ndarray | WaveformVariable | float":
        return np.log(arguments[0])

    def exp(self, arguments: list) -> "np.ndarray | WaveformVariable | float":
        return np.exp(arguments[0])
