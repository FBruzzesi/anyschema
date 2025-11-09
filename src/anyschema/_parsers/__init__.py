from __future__ import annotations

from importlib.util import find_spec

from anyschema._parsers.py_types import parse_py_type_into_nw_dtype

if find_spec("annotated_types") is not None:
    from anyschema._parsers.annotated_types import parse_integer_constraints, parse_multiple_of_constraints

    __all__ = ("parse_integer_constraints", "parse_multiple_of_constraints", "parse_py_type_into_nw_dtype")

else:
    __all__ = ("parse_py_type_into_nw_dtype",)
