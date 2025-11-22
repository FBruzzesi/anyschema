from __future__ import annotations

from types import NoneType
from typing import Optional, Union

import narwhals as nw
import pytest

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers.base import ParserChain
from anyschema.parsers.py_types import PyTypeParser
from anyschema.parsers.union_types import UnionTypeParser


@pytest.fixture
def parser() -> UnionTypeParser:
    """Create a UnionTypeParser instance with parser_chain set."""
    union_parser = UnionTypeParser()
    py_parser = PyTypeParser()
    chain = ParserChain([union_parser, py_parser])
    union_parser.parser_chain = chain
    py_parser.parser_chain = chain
    return union_parser


def test_parse_optional_int(parser: UnionTypeParser) -> None:
    """Test parsing Optional[int]."""
    result = parser.parse(Optional[int])
    assert result == nw.Int64()


def test_parse_optional_str(parser: UnionTypeParser) -> None:
    """Test parsing Optional[str]."""
    result = parser.parse(Optional[str])
    assert result == nw.String()


def test_parse_optional_float(parser: UnionTypeParser) -> None:
    """Test parsing Optional[float]."""
    result = parser.parse(Optional[float])
    assert result == nw.Float64()


def test_parse_optional_bool(parser: UnionTypeParser) -> None:
    """Test parsing Optional[bool]."""
    result = parser.parse(Optional[bool])
    assert result == nw.Boolean()


def test_parse_int_or_none(parser: UnionTypeParser) -> None:
    """Test parsing int | None (PEP 604 syntax)."""
    result = parser.parse(int | None)
    assert result == nw.Int64()


def test_parse_str_or_none(parser: UnionTypeParser) -> None:
    """Test parsing str | None."""
    result = parser.parse(str | None)
    assert result == nw.String()


def test_parse_none_or_int(parser: UnionTypeParser) -> None:
    """Test parsing None | int (reversed order)."""
    result = parser.parse(None | int)
    assert result == nw.Int64()


def test_parse_none_or_str(parser: UnionTypeParser) -> None:
    """Test parsing None | str (reversed order)."""
    result = parser.parse(None | str)
    assert result == nw.String()


def test_parse_union_int_none(parser: UnionTypeParser) -> None:
    """Test parsing Union[int, None]."""
    result = parser.parse(Union[int, None])
    assert result == nw.Int64()


def test_parse_union_none_str(parser: UnionTypeParser) -> None:
    """Test parsing Union[None, str] (reversed order)."""
    result = parser.parse(Union[None, str])
    assert result == nw.String()


def test_parse_optional_with_metadata(parser: UnionTypeParser) -> None:
    """Test parsing Optional with metadata (metadata should be preserved)."""
    # In a real scenario, metadata would affect the parsing through AnnotatedTypesParser
    # Here we just verify metadata is passed through correctly
    result = parser.parse(Optional[int], metadata=("test_metadata",))
    # Since PyTypeParser doesn't use metadata for int, it's just Int64
    assert result == nw.Int64()


def test_parse_union_preserves_metadata(parser: UnionTypeParser) -> None:
    """Test that parsing Union preserves outer metadata."""
    result = parser.parse(int | None, metadata=("outer", "metadata"))
    # Metadata is preserved but PyTypeParser doesn't use it for basic types
    assert result == nw.Int64()


def test_parse_union_three_types_raises(parser: UnionTypeParser) -> None:
    """Test parsing Union with three types raises UnsupportedDTypeError."""
    expected_msg = "Union with more than two types is not supported."
    with pytest.raises(UnsupportedDTypeError, match=expected_msg):
        parser.parse(Union[int, str, float])


def test_parse_union_three_types_pep604_raises(parser: UnionTypeParser) -> None:
    """Test parsing Union with three types (PEP 604) raises."""
    expected_msg = "Union with more than two types is not supported."
    with pytest.raises(UnsupportedDTypeError, match=expected_msg):
        parser.parse(int | str | float)


def test_parse_union_four_types_raises(parser: UnionTypeParser) -> None:
    """Test parsing Union with four types raises."""
    expected_msg = "Union with more than two types is not supported."
    with pytest.raises(UnsupportedDTypeError, match=expected_msg):
        parser.parse(Union[int, str, float, bool])


def test_parse_union_both_not_none_raises(parser: UnionTypeParser) -> None:
    """Test parsing Union with both types non-None raises."""
    expected_msg = "Union with both types being not None is not supported."
    with pytest.raises(UnsupportedDTypeError, match=expected_msg):
        parser.parse(Union[int, str])


def test_parse_union_both_not_none_pep604_raises(parser: UnionTypeParser) -> None:
    """Test parsing Union with both types non-None (PEP 604) raises."""
    expected_msg = "Union with both types being not None is not supported."
    with pytest.raises(UnsupportedDTypeError, match=expected_msg):
        parser.parse(int | str)


def test_parse_union_float_bool_raises(parser: UnionTypeParser) -> None:
    """Test parsing Union[float, bool] raises."""
    expected_msg = "Union with both types being not None is not supported."
    with pytest.raises(UnsupportedDTypeError, match=expected_msg):
        parser.parse(Union[float, bool])


def test_parse_int_returns_none(parser: UnionTypeParser) -> None:
    """Test parsing plain int returns None (not a Union)."""
    result = parser.parse(int)
    assert result is None


def test_parse_str_returns_none(parser: UnionTypeParser) -> None:
    """Test parsing plain str returns None (not a Union)."""
    result = parser.parse(str)
    assert result is None


def test_parse_list_returns_none(parser: UnionTypeParser) -> None:
    """Test parsing list[int] returns None (not a Union)."""
    result = parser.parse(list[int])
    assert result is None


def test_parse_none_type_returns_none(parser: UnionTypeParser) -> None:
    """Test parsing NoneType returns None (not a Union, just None)."""
    result = parser.parse(NoneType)
    assert result is None


def test_parse_optional_list(parser: UnionTypeParser) -> None:
    """Test parsing Optional[list[int]]."""
    result = parser.parse(Optional[list[int]])
    assert result == nw.List(nw.Int64())


def test_parse_optional_tuple(parser: UnionTypeParser) -> None:
    """Test parsing Optional[tuple[str, ...]]."""
    result = parser.parse(Optional[tuple[str, ...]])
    assert result == nw.List(nw.String())


def test_parse_list_or_none(parser: UnionTypeParser) -> None:
    """Test parsing list[str] | None."""
    result = parser.parse(list[str] | None)
    assert result == nw.List(nw.String())


def test_parse_none_or_list(parser: UnionTypeParser) -> None:
    """Test parsing None | list[float]."""
    result = parser.parse(None | list[float])
    assert result == nw.List(nw.Float64())


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (Optional[int], nw.Int64()),
        (Optional[str], nw.String()),
        (Optional[float], nw.Float64()),
        (Optional[bool], nw.Boolean()),
        (int | None, nw.Int64()),
        (str | None, nw.String()),
        (None | int, nw.Int64()),
        (None | str, nw.String()),
        (Union[int, None], nw.Int64()),
        (Union[None, str], nw.String()),
        (Optional[list[int]], nw.List(nw.Int64())),
        (list[str] | None, nw.List(nw.String())),
    ],
)
def test_parse_optional_types_parametrized(input_type: type, expected: nw.DType) -> None:
    """Parametrized test for Optional/Union types."""
    union_parser = UnionTypeParser()
    py_parser = PyTypeParser()
    chain = ParserChain([union_parser, py_parser])
    union_parser.parser_chain = chain
    py_parser.parser_chain = chain

    result = union_parser.parse(input_type)
    assert result == expected


@pytest.mark.parametrize(
    ("input_type", "error_msg"),
    [
        (Union[int, str, float], "Union with more than two types is not supported."),
        (int | str | float, "Union with more than two types is not supported."),
        (Union[int, str], "Union with both types being not None is not supported."),
        (int | str, "Union with both types being not None is not supported."),
        (float | bool, "Union with both types being not None is not supported."),
    ],
)
def test_parse_unsupported_unions_parametrized(input_type: type, error_msg: str) -> None:
    """Parametrized test for unsupported Union types."""
    union_parser = UnionTypeParser()
    py_parser = PyTypeParser()
    chain = ParserChain([union_parser, py_parser])
    union_parser.parser_chain = chain
    py_parser.parser_chain = chain

    with pytest.raises(UnsupportedDTypeError, match=error_msg):
        union_parser.parse(input_type)
