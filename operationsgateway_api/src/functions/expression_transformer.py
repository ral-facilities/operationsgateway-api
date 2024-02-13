from lark import Transformer
import numpy as np

from operationsgateway_api.src.functions.builtins.builtins import Builtins
from operationsgateway_api.src.functions.parser import parser
from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


class ExpressionTransformer(Transformer):
    def __init__(self, channels: dict, visit_tokens: bool = True) -> None:
        """
        Store `channels` (input variables) and initialise the Lark Transformer
        for evaluating expressions.
        """
        self.channels = channels
        super().__init__(visit_tokens)

    def evaluate(self, expression: str) -> "np.ndarray | WaveformVariable | float":
        """
        Parse `expression` and return the value from evaluating it.
        """
        tree = parser.parse(expression)
        return self.transform(tree)

    # Values
    def constant(self, number) -> float:
        (number,) = number
        return float(number)

    def variable(self, channel_name) -> "np.ndarray | WaveformVariable | float":
        (channel_name,) = channel_name
        return self.channels[str(channel_name)]

    # Operations
    def subtraction(self, operands) -> "np.ndarray | WaveformVariable | float":
        return operands[0] - operands[1]

    def addition(self, operands) -> "np.ndarray | WaveformVariable | float":
        print(operands)
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
