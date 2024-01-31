from lark import Lark


parser = Lark(
    r"""
    ?term         : SIGNED_NUMBER -> constant
                  | CNAME -> variable
                  | function
                  | operation
                  | "(" term ")"

    ?operation    : subtraction
                  | addition
                  | multiplication
                  | division
                  | exponentiation

    subtraction   : term "-" term
    addition      : term "+" term
    multiplication: term "*" term
    division      : term "/" term
    exponentiation: term "**" term

    ?function     : mean
                  | min
                  | max
                  | log
                  | exp
                  | rising
                  | falling
                  | centre
                  | fwhm
                  | background
                  | integrate
                  | centroid_x
                  | centroid_y
                  | fwhm_x
                  | fwhm_y
                  | unknown

    mean          : "mean(" term ")"
    min           : "min(" term ")"
    max           : "max(" term ")"
    log           : "log(" term ")"
    exp           : "exp(" term ")"
    rising        : "rising(" term ")"
    falling       : "falling(" term ")"
    centre        : "centre(" term ")"
    fwhm          : "fwhm(" term ")"
    background    : "background(" term ")"
    integrate     : "integrate(" term ")"
    centroid_x    : "centroid_x(" term ")"
    centroid_y    : "centroid_y(" term ")"
    fwhm_x        : "fwhm_x(" term ")"
    fwhm_y        : "fwhm_y(" term ")"
    unknown       : CNAME "(" term ")"

    %import common.CNAME
    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
""",
    start="term",
)
