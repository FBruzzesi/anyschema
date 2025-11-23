from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, ForwardRef, Optional

import narwhals as nw
import pytest

from anyschema.parsers import ForwardRefParser, ParserChain, PyTypeParser, UnionTypeParser


def forward_ref_parser_builder(globalns: dict | None = None, localns: dict | None = None) -> ForwardRefParser:
    forward_ref_parser = ForwardRefParser(globalns=globalns, localns=localns)
    union_parser = UnionTypeParser()
    py_parser = PyTypeParser()
    chain = ParserChain([forward_ref_parser, union_parser, py_parser])
    forward_ref_parser.parser_chain = chain
    union_parser.parser_chain = chain
    py_parser.parser_chain = chain
    return forward_ref_parser


@pytest.fixture(scope="module")
def forward_ref_parser() -> ForwardRefParser:
    """Create a ForwardRefParser instance with parser_chain set."""
    return forward_ref_parser_builder()


class CustomType:
    pass


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        ("int", nw.Int64()),
        ("str", nw.String()),
        ("float", nw.Float64()),
        ("bool", nw.Boolean()),
        ("list[int]", nw.List(nw.Int64())),
        ("list[str]", nw.List(nw.String())),
        ("tuple[int, ...]", nw.List(nw.Int64())),
        ("List[int]", nw.List(nw.Int64())),
        ("int | None", nw.Int64()),
        ("Optional[int]", nw.Int64()),
    ],
)
def test_forward_ref(forward_ref_parser: ForwardRefParser, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = forward_ref_parser.parse(input_type=ForwardRef(input_type))
    assert result == expected


@pytest.mark.parametrize(
    "input_type",
    [
        int,
        str,
        list[int],
    ],
)
def test_non_forward_ref(forward_ref_parser: ForwardRefParser, input_type: Any) -> None:
    result = forward_ref_parser.parse(input_type=input_type)
    assert result is None


@pytest.mark.parametrize(
    ("type_string", "expected"),
    [
        ("int", int),
        ("str", str),
        ("list[int]", list[int]),
        ("Optional[str]", Optional[str]),
    ],
)
def test_evaluate_string(forward_ref_parser: ForwardRefParser, type_string: str, expected: type) -> None:
    result = forward_ref_parser._evaluate_string(type_string)
    assert result == expected


def test_evaluate_string_name_error(forward_ref_parser: ForwardRefParser) -> None:
    with pytest.raises(NameError):
        forward_ref_parser._evaluate_string("UndefinedType")


def test_custom_globals() -> None:
    custom_globals = {
        "CustomType": int,  # Custom class to a parsable type
        "str": bool,  # don't do this in production
    }
    parser = forward_ref_parser_builder(globalns=custom_globals)
    result = parser.parse(ForwardRef("CustomType"))
    assert result == nw.Int64()

    result = parser.parse(ForwardRef("str"))
    assert result == nw.Boolean()


def test_custom_local() -> None:
    class LocalClass:
        pass

    parser = forward_ref_parser_builder(localns={"LocalClass": int})
    result = parser.parse(ForwardRef("LocalClass"))
    assert result == nw.Int64()


@pytest.mark.parametrize(
    ("input_type", "context"),
    [
        ("UndefinedType", pytest.raises(NotImplementedError, match="Failed to resolve ForwardRef")),
        ("list[", pytest.raises(SyntaxError, match="Forward reference must be an expression")),
        ("1 + 1", pytest.raises(NotImplementedError, match="No parser in chain could handle type")),
    ],
)
def test_resolution_error(
    forward_ref_parser: ForwardRefParser, input_type: str, context: AbstractContextManager[Any]
) -> None:
    with context:
        forward_ref_parser.parse(ForwardRef(input_type))


def test_build_namespace_default(forward_ref_parser: ForwardRefParser) -> None:
    # Globals
    assert forward_ref_parser.globalns["int"] is int
    assert forward_ref_parser.globalns["str"] is str
    assert forward_ref_parser.globalns["float"] is float
    assert forward_ref_parser.globalns["bool"] is bool
    assert forward_ref_parser.globalns["list"] is list
    assert "Optional" in forward_ref_parser.globalns
    assert "Union" in forward_ref_parser.globalns
    assert "List" in forward_ref_parser.globalns

    # Locals
    assert forward_ref_parser.localns == {}


def test_build_namespace_custom() -> None:
    custom_globals = {"CustomType": CustomType, "MyInt": int, "bool": str}
    custom_locals = {"local_var": int}
    parser = forward_ref_parser_builder(globalns=custom_globals, localns=custom_locals)

    # Check that custom types are in the namespace
    assert parser.globalns["CustomType"] is CustomType
    assert parser.globalns["MyInt"] is int
    # Built-ins should still be there
    assert parser.globalns["int"] is int
    assert parser.globalns["str"] is str

    assert parser.globalns["bool"] is str

    assert parser.localns == custom_locals
