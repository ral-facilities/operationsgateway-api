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

    def __init__(
        self,
        channels: "dict[str, float | WaveformVariable | np.ndarray]",
    ) -> None:
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
    def constant(self, tokens: list) -> float:
        (number,) = tokens
        return float(number)

    def variable(self, tokens: list) -> "np.ndarray | WaveformVariable | float":
        return self.channels["".join(tokens)]

    # Operations
    def subtraction(self, tokens: list) -> "np.ndarray | WaveformVariable | float":
        left_operand, right_operand = tokens
        return left_operand - right_operand

    def addition(self, tokens: list) -> "np.ndarray | WaveformVariable | float":
        left_operand, right_operand = tokens
        return left_operand + right_operand

    def multiplication(self, tokens: list) -> "np.ndarray | WaveformVariable | float":
        left_operand, right_operand = tokens
        return left_operand * right_operand

    def division(self, tokens: list) -> "np.ndarray | WaveformVariable | float":
        left_operand, right_operand = tokens
        return left_operand / right_operand

    def exponentiation(self, tokens: list) -> "np.ndarray | WaveformVariable | float":
        left_operand, right_operand = tokens
        return left_operand**right_operand

    # Functions
    def builtin(self, tokens: list) -> "np.ndarray | WaveformVariable | float":
        return Builtins.evaluate(tokens)

    def mean(self, tokens: list) -> float:
        (argument,) = tokens
        return np.mean(argument)

    def min(self, tokens: list) -> float:  # noqa: A003
        (argument,) = tokens
        return np.min(argument)

    def max(self, tokens: list) -> float:  # noqa: A003
        (argument,) = tokens
        return np.max(argument)

    def log(self, tokens: list) -> "np.ndarray | WaveformVariable | float":
        (argument,) = tokens
        return np.log(argument)

    def exp(self, tokens: list) -> "np.ndarray | WaveformVariable | float":
        (argument,) = tokens
        return np.exp(argument)
