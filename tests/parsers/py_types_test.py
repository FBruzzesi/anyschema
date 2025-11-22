from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum

import narwhals as nw
import pytest

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers.base import ParserChain
from anyschema.parsers.py_types import PyTypeParser


class Color(Enum):
    """Example enum for testing."""

    RED = 1
    GREEN = 2
    BLUE = 3


class Status(Enum):
    """Another enum for testing."""

    ACTIVE = "active"
    INACTIVE = "inactive"


@pytest.fixture
def parser() -> PyTypeParser:
    """Create a PyTypeParser instance with parser_chain set."""
    parser = PyTypeParser()
    chain = ParserChain([parser])
    parser.parser_chain = chain
    return parser


def test_parse_int(parser: PyTypeParser) -> None:
    """Test parsing int type."""
    result = parser.parse(int)
    assert result == nw.Int64()


def test_parse_float(parser: PyTypeParser) -> None:
    """Test parsing float type."""
    result = parser.parse(float)
    assert result == nw.Float64()


def test_parse_str(parser: PyTypeParser) -> None:
    """Test parsing str type."""
    result = parser.parse(str)
    assert result == nw.String()


def test_parse_bool(parser: PyTypeParser) -> None:
    """Test parsing bool type."""
    result = parser.parse(bool)
    assert result == nw.Boolean()


def test_parse_datetime(parser: PyTypeParser) -> None:
    """Test parsing datetime type."""
    result = parser.parse(datetime)
    assert result == nw.Datetime("us")


def test_parse_date(parser: PyTypeParser) -> None:
    """Test parsing date type."""
    result = parser.parse(date)
    assert result == nw.Date()


def test_parse_timedelta(parser: PyTypeParser) -> None:
    """Test parsing timedelta type."""
    result = parser.parse(timedelta)
    assert result == nw.Duration()


def test_parse_time(parser: PyTypeParser) -> None:
    """Test parsing time type."""
    result = parser.parse(time)
    assert result == nw.Time()


def test_parse_decimal(parser: PyTypeParser) -> None:
    """Test parsing Decimal type."""
    result = parser.parse(Decimal)
    assert result == nw.Decimal()


def test_parse_bytes(parser: PyTypeParser) -> None:
    """Test parsing bytes type."""
    result = parser.parse(bytes)
    assert result == nw.Binary()


def test_parse_object(parser: PyTypeParser) -> None:
    """Test parsing object type."""
    result = parser.parse(object)
    assert result == nw.Object()


def test_parse_enum(parser: PyTypeParser) -> None:
    """Test parsing Enum type."""
    result = parser.parse(Color)
    assert result == nw.Enum(Color)


def test_parse_different_enum(parser: PyTypeParser) -> None:
    """Test parsing different Enum type."""
    result = parser.parse(Status)
    assert result == nw.Enum(Status)


def test_parse_unsupported_type(parser: PyTypeParser) -> None:
    """Test parsing unsupported type returns None."""

    class CustomClass:
        pass

    result = parser.parse(CustomClass)
    assert result is None


def test_parse_with_metadata(parser: PyTypeParser) -> None:
    """Test parsing with metadata (metadata is ignored for basic types)."""
    result = parser.parse(int, metadata=("some", "metadata"))
    assert result == nw.Int64()


def test_parse_list_int(parser: PyTypeParser) -> None:
    """Test parsing list[int]."""
    result = parser.parse(list[int])
    assert result == nw.List(nw.Int64())


def test_parse_list_str(parser: PyTypeParser) -> None:
    """Test parsing list[str]."""
    result = parser.parse(list[str])
    assert result == nw.List(nw.String())


def test_parse_list_float(parser: PyTypeParser) -> None:
    """Test parsing list[float]."""
    result = parser.parse(list[float])
    assert result == nw.List(nw.Float64())


def test_parse_list_bool(parser: PyTypeParser) -> None:
    """Test parsing list[bool]."""
    result = parser.parse(list[bool])
    assert result == nw.List(nw.Boolean())


def test_parse_list_no_args(parser: PyTypeParser) -> None:
    """Test parsing list without type arguments."""
    result = parser.parse(list)
    # List without args returns None (not a GenericAlias)
    assert result is None


def test_parse_sequence_int(parser: PyTypeParser) -> None:
    """Test parsing Sequence[int]."""
    result = parser.parse(Sequence[int])
    assert result == nw.List(nw.Int64())


def test_parse_sequence_str(parser: PyTypeParser) -> None:
    """Test parsing Sequence[str]."""
    result = parser.parse(Sequence[str])
    assert result == nw.List(nw.String())


def test_parse_sequence_no_args(parser: PyTypeParser) -> None:
    """Test parsing Sequence without type arguments."""
    result = parser.parse(Sequence)
    # Sequence without args returns None (not a GenericAlias)
    assert result is None


def test_parse_iterable_int(parser: PyTypeParser) -> None:
    """Test parsing Iterable[int]."""
    result = parser.parse(Iterable[int])
    assert result == nw.List(nw.Int64())


def test_parse_iterable_str(parser: PyTypeParser) -> None:
    """Test parsing Iterable[str]."""
    result = parser.parse(Iterable[str])
    assert result == nw.List(nw.String())


def test_parse_iterable_no_args(parser: PyTypeParser) -> None:
    """Test parsing Iterable without type arguments."""
    result = parser.parse(Iterable)
    # Iterable without args returns None (not a GenericAlias)
    assert result is None


def test_parse_tuple_homogeneous_ellipsis(parser: PyTypeParser) -> None:
    """Test parsing tuple[int, ...] (variable length homogeneous tuple)."""
    result = parser.parse(tuple[int, ...])
    assert result == nw.List(nw.Int64())


def test_parse_tuple_homogeneous_fixed(parser: PyTypeParser) -> None:
    """Test parsing tuple[int, int, int] (fixed length homogeneous tuple)."""
    result = parser.parse(tuple[int, int, int])
    assert result == nw.Array(nw.Int64(), shape=3)


def test_parse_tuple_homogeneous_fixed_different_length(parser: PyTypeParser) -> None:
    """Test parsing tuple with different fixed length."""
    result = parser.parse(tuple[str, str, str, str, str])
    assert result == nw.Array(nw.String(), shape=5)


def test_parse_tuple_heterogeneous_raises(parser: PyTypeParser) -> None:
    """Test parsing tuple with mixed types raises UnsupportedDTypeError."""
    with pytest.raises(UnsupportedDTypeError, match="Tuple with mixed types is not supported"):
        parser.parse(tuple[int, str])


def test_parse_tuple_heterogeneous_three_types_raises(parser: PyTypeParser) -> None:
    """Test parsing tuple with three different types raises."""
    with pytest.raises(UnsupportedDTypeError, match="Tuple with mixed types is not supported"):
        parser.parse(tuple[int, str, float])


def test_parse_tuple_no_args(parser: PyTypeParser) -> None:
    """Test parsing tuple without type arguments."""
    result = parser.parse(tuple)
    # Tuple without args returns None (not a GenericAlias)
    assert result is None


def test_parse_nested_list(parser: PyTypeParser) -> None:
    """Test parsing nested list[list[int]]."""
    result = parser.parse(list[list[int]])
    assert result == nw.List(nw.List(nw.Int64()))


def test_parse_nested_sequence(parser: PyTypeParser) -> None:
    """Test parsing nested Sequence[Sequence[str]]."""
    result = parser.parse(Sequence[Sequence[str]])
    assert result == nw.List(nw.List(nw.String()))


def test_parse_generic_type_with_metadata(parser: PyTypeParser) -> None:
    """Test parsing generic type with metadata (metadata is passed through)."""
    # Metadata is not used by PyTypeParser for generic types, but should not cause errors
    result = parser.parse(list[int], metadata=("some", "metadata"))
    assert result == nw.List(nw.Int64())


def test_parse_none_type_returns_none(parser: PyTypeParser) -> None:
    """Test parsing None type returns None (not handled by this parser)."""
    from types import NoneType

    result = parser.parse(NoneType)
    assert result is None


def test_parse_dict_returns_none(parser: PyTypeParser) -> None:
    """Test parsing dict returns None (not supported)."""
    result = parser.parse(dict)
    assert result is None


def test_parse_set_returns_none(parser: PyTypeParser) -> None:
    """Test parsing set returns None (not supported)."""
    result = parser.parse(set)
    assert result is None


def test_parse_frozenset_returns_none(parser: PyTypeParser) -> None:
    """Test parsing frozenset returns None (not supported)."""
    result = parser.parse(frozenset)
    assert result is None


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (int, nw.Int64()),
        (float, nw.Float64()),
        (str, nw.String()),
        (bool, nw.Boolean()),
        (datetime, nw.Datetime("us")),
        (date, nw.Date()),
        (timedelta, nw.Duration()),
        (time, nw.Time()),
        (Decimal, nw.Decimal()),
        (bytes, nw.Binary()),
        (object, nw.Object()),
    ],
)
def test_parse_basic_types_parametrized(input_type: type, expected: nw.DType) -> None:
    """Parametrized test for basic Python types."""
    parser = PyTypeParser()
    chain = ParserChain([parser])
    parser.parser_chain = chain

    result = parser.parse(input_type)
    assert result == expected


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (list[int], nw.List(nw.Int64())),
        (list[str], nw.List(nw.String())),
        (list[float], nw.List(nw.Float64())),
        (list[bool], nw.List(nw.Boolean())),
        (Sequence[int], nw.List(nw.Int64())),
        (Iterable[str], nw.List(nw.String())),
        (tuple[int, ...], nw.List(nw.Int64())),
        (tuple[str, str, str], nw.Array(nw.String(), shape=3)),
    ],
)
def test_parse_generic_types_parametrized(input_type: type, expected: nw.DType) -> None:
    """Parametrized test for generic types."""
    parser = PyTypeParser()
    chain = ParserChain([parser])
    parser.parser_chain = chain

    result = parser.parse(input_type)
    assert result == expected
