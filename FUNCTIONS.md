# Functions

In OperationsGateway, "functions" is a feature by which users can define their own outputs from a records channel data, using predefined builtin functions and common mathematical operators. This functionality is described here from a developers perspective, explaining relevant concepts and how to develop the functionality further as needed.

## Terminology
Various terms are used, perhaps not always consistently, in the codebase. Some of these are exclusively used in the context of functions, whilst others are more widely used across the codebase.
- `function`: General term for a single combination of `name` and `expression` defined by the user, to be evaluated on each `record` currently loaded in the UI. It may depend on one or more of the following:
    - `constant`: Explicit numerical value not dependent on the `record` in question, for example `0.1` or `123`.
    - `variable`: Non-numeric string describing a value that **is** dependent on the record, either:
        - The name of a `channel`.
        - The `name` of another `function`, which has already been evaluated for this record.
    - `operand`: Symbol representing a mathematical operation, one of `+`, `-`, `*`, `/` and `**`.
    - `builtin`: A predefined function which is applied to user defined input. This may be simple and just use a `numpy` implementation, such `np.mean`. It may be more complex and require custom functionality, such as determining the `background` of a signal.
- `name`: String identifying a `function`, so that it can be used as an input to other user defined `function`s.
- `expression`: String defining operations to be applied to each record, following the supported syntax.
- `return type` or `data type`: Channels can either be "scalar" (`float`), "waveform" (two `np.ndarray`s for x and y) or "image" (one 2D `np.ndarray`). Similarly, the output of any `function` or any intermediary `operand` or `builtin` will be one of these types.

## Lark
To implement functions, we use the [Lark](https://github.com/lark-parser/lark) library. As a starting point, the [JSON parser tutorial](https://github.com/lark-parser/lark/blob/master/docs/json_tutorial.md) introduces the crucial concepts for building a parser and `Transformer`.

### Parser
To parse an `expression`, suitable grammar must be defined. This is done in [`parser.py`](operationsgateway_api/src/functions/parser.py), and the same grammar is used for all [transformations](#transformers).

The format of the grammar uses the basic Lark concepts covered in the JSON tutorial. "Rules" such as `operation` have multiple possible patterns to match against, which are "rules" in their own right such as `addition`. This can refer back to more generic rules, such as `term`. Ultimately, each rule will be evaluated until it can be expressed in terms of "terminals", which are either literal strings (e.g. `"+"` for addition) or regex (`CNAME` and `SIGNED_NUMBER` are predefined regex patterns we import). For a more in depth discussion of grammar, please refer to the Lark documentation.

To expand the grammar, additional patterns can be added here. For example, other `operation`s such as floor division would need to be defined under that rule as:
```
    ?operation    : subtraction
                  | addition
                  | multiplication
                  | division
                  | exponentiation
                  | floor_division

    floor_division: term "//" term
```

Once defined, the parser is then used to convert a string into a `ParseTree` of `Token`s, based on the defined grammar. However, in our use case we do not display or pass the expression in this format so this can be mostly ignored.

### Transformers
Once an `expression` is parsed, we then need to transform it into something useful. What this output is can vary, but in all cases the grammar (and so parser) is the same. Currently there are three parsers (see their docstrings for implementation details):
- [`TypeTransformer`](operationsgateway_api/src/functions/type_transformer.py)
- [`VariableTransformer`](operationsgateway_api/src/functions/variable_transformer.py)
- [`ExpressionTransformer`](operationsgateway_api/src/functions/expression_transformer.py)

The primary feature of all of these is their callback functions. When transforming the tree, Lark will look for a function on the transformer with the name matching the token being transformed (i.e. one of the rules from the parser). If found, this will be called with the **list** of `Token`s as the argument. So for any `operation`, you will have two `Token`s - the `term` to the left and right of the actual operator (e.g. `"+"`).

This allow us to, for example, define the callback function `variable` which, respectively:
- Lookup the dtype of the channel in the manifest and to ensure it is being passed to builtins which accept its type
- Build a set of channel names which feature in the `expression`
- Return the numerical value of that channel for the given record to be used in the final calculation

To extend this functionality, using floor division as an example, one would need to add a callback to `TypeTransformer` to identify it as an operation which has requirements on which types can be used together **and** `ExpressionTransformer` to actually perform the division. It would not be necessary to add it to `VariableTransformer`, as it is not relevant for channel name identification.

## Builtins
One of the main features of "functions" is the ability for users to apply predefined, non-trivial analysis to a channel. Since these are more complex, they are defined separately from the Lark classes.

Each new builtin should extend the abstract [`Builtin`](operationsgateway_api/src/functions/builtins/builtin.py) class, which defines the basic properties that identify it and crucially, the implementation details in the `evaluate` function.

A reference should also be added to `builtins_dict` on [`Builtin`](operationsgateway_api/src/functions/builtins/builtins.py). This is called by the Lark `Transformer`s when needed, and does a lookup of the function name before calling `evaluate` from the correct class.

It should be noted, that the distinction between purely `numpy` functions and `builtin` functions is somewhat arbitrary - it would be possible to represent all `builtin` functions directly on the Lark classes like the former, however this introduces a lot of complexity in those classes, and means type checking and evaluations for a given builtin would be split across different `Transformer`s. Likewise all the `numpy` functions could be refactored into their own classes, however given their (relative) simplicity and the fact they are unlikely to be regularly modified, this has not (yet) been done.

## Data representation
Of the three data types, "scalar" and "image" are already well represented, and support operations such as addition and multiplication. However, "waveform" is not. In principle therefore, it is necessary to define methods for how a data type behaves when these operations are applied. If more data types are developed in the future, or custom behaviour is needed for "scalar" or "image", then the pattern of `WaveformVariable` should be extended to those use cases.

### WaveformVariable
The [`WaveformVariable`](operationsgateway_api/src/functions/waveform_variable.py) class achieves this by defining dunder methods for `__add__`, `__sub__` and so on. Note that for commutative operations like the former, the definition of `__radd__` is trivial, but needs to be explicit for non-commutative operations like subtraction. Generally speaking, all these operations are applied to the y axis of the data, but the x axis is persisted and so the output remains a `WaveformVariable`.

As we use `numpy` for much of the implementation details, we also define functions for `min`, `mean` etc. These will be called so that the syntax for a `WaveformVariable`:
```python
>>> import numpy as np
>>> from operationsgateway_api.src.functions.waveform_variable import WaveformVariable
>>> np.mean(WaveformVariable(x=np.array([1,2,3]), y=np.array([1,4,9])))
4.666666666666667
```
is the same as that of "image" or "scalar":
```python
>>> np.mean(1)
1.0
```
In this case, the output is typically a "scalar"; the applied function reduces the dimensionality of the input. In the process, the x axis data is discarded.

It may be necessary to define additional builtin functions (e.g. `np.median` as `median`) or operators (e.g. `//` as `__floordiv__`), in which case these will also need to be referenced here so that they can be applied to data of the type "waveform".

