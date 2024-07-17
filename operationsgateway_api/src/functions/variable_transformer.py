from lark import Transformer

from operationsgateway_api.src.functions.parser import parser


class VariableTransformer(Transformer):
    """Subclass of the Lark `Transformer` for extracting variable names from an
    expression.

    The purpose of a Lark `Transformer` is to `transform` a `ParseTree` of
    `Token`s into some other format. To achieve this, callback functions defined
    on the class are called whenever a matching `Token` with that name is
    encountered in the `ParseTree`.

    For utility, the `evaluate` function accepts a `str` and performs the
    parsing under the hood.

    Attributes:
        variables (set):
            Record of all variable names encountered when evaluating the
            expression, once populated can be used for looking up channel data.
            Note this may also include names for other function outputs.

    Examples:
        >>> variable_transformer = VariableTransformer()
        >>> variable_transformer.evaluate("(channel_1 + function_1) / 2")
        >>> variable_transformer.variables
        {'channel_1', 'function_1'}
    """

    def __init__(self) -> None:
        """Initialises the Transformer and creates an empty set for recording
        `variables` and dependencies on other functions to be skipped in the case they
        cannot be defined for this particular record.
        """
        self.variables = set()
        self.skip_functions = set()
        super().__init__()

    def evaluate(self, expression: str) -> None:
        """Parse and transform `expression`, recording the input variables of
        the expression in the process.

        Args:
            expression (str): Expression to be evaluated for variable names.
        """
        tree = parser.parse(expression)
        self.transform(tree)

    # Transformer callback functions
    def variable(self, tokens: list) -> list:
        self.variables.add("".join(tokens))
        return tokens
