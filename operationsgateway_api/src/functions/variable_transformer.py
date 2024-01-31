from lark import Transformer

from operationsgateway_api.src.functions.parser import parser


class VariableTransformer(Transformer):
    def __init__(self, visit_tokens: bool = True) -> None:
        """
        Creates an empty set for recording any input variables and initialise
        the Lark Transformer for evaluating variables.
        """
        self.variables = set()
        super().__init__(visit_tokens)

    def evaluate(self, expression: str) -> None:
        """
        Parse `expression` and record the variables it depends on as inputs.
        """
        tree = parser.parse(expression)
        self.transform(tree)

    def variable(self, channel_name: list) -> list:
        self.variables.add(str(channel_name[0]))
        return channel_name
