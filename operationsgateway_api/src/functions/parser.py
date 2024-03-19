from lark import Lark


parser = Lark(
    r"""
    ?term         : SIGNED_NUMBER -> constant
                  | variable
                  | function
                  | operation
                  | "(" term ")"

    variable      : LETTER (SEPARATOR|LETTER|DIGIT)*
    SEPARATOR     : ("_"|"-")

    ?operation    : subtraction
                  | addition
                  | multiplication
                  | division
                  | exponentiation

    subtraction   : term " - " term
    addition      : term " + " term
    multiplication: term " * " term
    division      : term " / " term
    exponentiation: term "**" term

    ?function     : mean
                  | min
                  | max
                  | log
                  | exp
                  | builtin

    mean          : "mean(" term ")"
    min           : "min(" term ")"
    max           : "max(" term ")"
    log           : "log(" term ")"
    exp           : "exp(" term ")"
    builtin       : CNAME "(" term ")"

    %import common.CNAME
    %import common.DIGIT
    %import common.LETTER
    %import common.SIGNED_NUMBER
    %import common.WS
""",
    start="term",
)
