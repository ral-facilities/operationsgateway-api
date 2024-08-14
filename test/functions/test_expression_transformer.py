from lark import LarkError
import numpy as np
import pytest

from operationsgateway_api.src.functions.expression_transformer import (
    ExpressionTransformer,
)


class TestExpressionTransformer:
    @pytest.mark.parametrize(
        "expression, expected_result",
        [
            pytest.param("36 / 6 * 3 + 2**2 - (3 + 5)", 14, id="BIDMAS"),
            pytest.param("min(a)", 0, id="Min"),
            pytest.param("max(a)", 3, id="Max"),
            pytest.param("mean(a)", 1.5, id="Mean"),
            pytest.param("log(1)", 0, id="Log"),
            pytest.param("exp(0)", 1, id="Exp"),
        ],
    )
    def test_expression_transformer(
        self,
        expression: str,
        expected_result: float,
    ):
        channels = {"a": np.array([[0, 1], [2, 3]])}
        expression_transformer = ExpressionTransformer(channels)
        result = expression_transformer.evaluate(expression)
        assert result == expected_result

    def test_expression_transformer_unknown_function(self):
        expression_transformer = ExpressionTransformer({})
        with pytest.raises(LarkError) as e:
            expression_transformer.evaluate("unknown(1)")

        expected_message = (
            'Error trying to process rule "builtin":\n\n'
            "'unknown' is not a recognised builtin function name"
        )
        assert str(e.value) == expected_message
