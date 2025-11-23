from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from types import NoneType
from typing import Any

import narwhals as nw
import pytest

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers import ParserChain, PyTypeParser, UnionTypeParser


class Color(Enum):
    """Example enum for testing."""

    RED = 1
    GREEN = 2
    BLUE = 3


class Status(Enum):
    """Another enum for testing."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class CustomClass:
    pass


@pytest.fixture(scope="module")
def py_type_parser() -> PyTypeParser:
    """Create a PyTypeParser instance with parser_chain set."""
    union_parser = UnionTypeParser()
    py_parser = PyTypeParser()
    chain = ParserChain([union_parser, py_parser])
    union_parser.parser_chain = chain
    py_parser.parser_chain = chain
    return py_parser


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
        (Color, nw.Enum(Color)),
        (Status, nw.Enum(Status)),
    ],
)
def test_parse_non_nested(py_type_parser: PyTypeParser, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = py_type_parser.parse(input_type)
    assert result == expected


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (list[int], nw.List(nw.Int64())),
        (list[str], nw.List(nw.String())),
        (list[float], nw.List(nw.Float64())),
        (list[bool], nw.List(nw.Boolean())),
        (list[list[int]], nw.List(nw.List(nw.Int64()))),
        (list[tuple[int, int]], nw.List(nw.Array(nw.Int64(), shape=2))),
        (Sequence[int], nw.List(nw.Int64())),
        (Sequence[str | None], nw.List(nw.String())),
        (Iterable[int], nw.List(nw.Int64())),
        (Iterable[str], nw.List(nw.String())),
        (Sequence[Sequence[str]], nw.List(nw.List(nw.String()))),
        (tuple[int | None, ...], nw.List(nw.Int64())),
        (tuple[int, int, int], nw.Array(nw.Int64(), shape=3)),
        (tuple[str, str], nw.Array(nw.String(), shape=2)),
        (list, nw.List(nw.Object())),
        (tuple, nw.List(nw.Object())),
        (Sequence, nw.List(nw.Object())),
        (Iterable, nw.List(nw.Object())),
    ],
)
def test_parse_nested(py_type_parser: PyTypeParser, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = py_type_parser.parse(input_type)
    assert result == expected


@pytest.mark.parametrize("input_type", [tuple[int, str], tuple[int, str, float]])
def test_parse_heterogeneous_tuple_raises(py_type_parser: PyTypeParser, input_type: Any) -> None:
    with pytest.raises(UnsupportedDTypeError, match="Tuple with mixed types is not supported"):
        py_type_parser.parse(input_type)


@pytest.mark.parametrize(("input_type", "expected"), [(int, nw.Int64()), (list[int], nw.List(nw.Int64()))])
def test_parse_with_metadata(py_type_parser: PyTypeParser, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = py_type_parser.parse(input_type, metadata=("some", "metadata"))
    assert result == expected


@pytest.mark.parametrize("input_type", [CustomClass, NoneType, dict, set[int], frozenset])
def test_unsupported_type(py_type_parser: PyTypeParser, input_type: Any) -> None:
    result = py_type_parser.parse(input_type)
    assert result is None
