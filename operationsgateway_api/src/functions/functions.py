import logging
import time

from cexprtk import Expression, Symbol_Table
import numpy as np


log = logging.getLogger()


class FunctionController:
    def __init__(self) -> None:
        self.symbols = {}
        self.definitions = ""
        self.shapes = []
        self.expression = None
        self.callback = None

    def add_scalar(self, symbol: str, value: float):
        self.symbols[symbol] = value

    def add_waveform(self, symbol: str, value: str):
        size = value.count(",") + 1
        array = value.replace("[", "{").replace("]", "}")
        self.definitions += f"var {symbol}[{size}] := {array}; "

    def add_image(self, symbol: str, value: np.ndarray):
        self.shapes.append({value.size: value.shape})
        array = "{" + ",".join(value.flatten().astype(str)) + "}"
        self.definitions += f"var {symbol}[{value.size}] := {array}; "

    def evaluate(self, t):
        log.debug("%s", time.time() - t)
        expression = Expression(
            f"{self.definitions} return [{self.expression}];",
            Symbol_Table(self.symbols, add_constants=True),
            self.callback,
        )
        log.debug("%s", time.time() - t)
        expression()
        log.debug("%s", time.time() - t)
        results = expression.results()[0]
        if isinstance(results, list):
            for size_shape in self.shapes:
                size = list(size_shape.keys())[0]
                if len(results) == size:
                    shape = size_shape[size]
                    log.debug("%s", time.time() - t)
                    return np.array(results).reshape(shape)

        log.debug("%s", time.time() - t)
        return results
