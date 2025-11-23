from __future__ import annotations

from typing import Any

import hypothesis.strategies as st
import narwhals as nw
import pytest
from annotated_types import Ge, Gt, Interval, Le, Lt
from hypothesis import given

from anyschema.parsers._base import ParserChain
from anyschema.parsers._builtin import PyTypeParser
from anyschema.parsers.annotated_types import AnnotatedTypesParser


@pytest.fixture(scope="module")
def annotated_types_parser() -> AnnotatedTypesParser:
    """Create an AnnotatedTypesParser instance with parser_chain set."""
    annotated_types_parser = AnnotatedTypesParser()
    py_parser = PyTypeParser()
    chain = ParserChain([annotated_types_parser, py_parser])
    annotated_types_parser.parser_chain = chain
    py_parser.parser_chain = chain
    return annotated_types_parser


@pytest.mark.parametrize("input_type", [int, str, float, list[int]])
def test_parse_non_annotated(annotated_types_parser: AnnotatedTypesParser, input_type: type) -> None:
    result = annotated_types_parser.parse(input_type)
    assert result is None


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ((Gt(0),), nw.UInt64()),
        ((Gt(-1),), nw.UInt64()),
        ((Gt(-100),), nw.Int64()),
        ((Gt(1000),), nw.UInt64()),
        ((Ge(0),), nw.UInt64()),
        ((Ge(1),), nw.UInt64()),
        ((Ge(-100),), nw.Int64()),
        ((Lt(10),), nw.Int64()),
        ((Lt(-100),), nw.Int64()),
        ((Le(10),), nw.Int64()),
        ((Le(-100),), nw.Int64()),
        ((Interval(ge=0, le=100),), nw.UInt8()),
        ((Interval(gt=0, lt=100),), nw.UInt8()),
        ((Interval(ge=-100, le=100),), nw.Int8()),
        ((Interval(ge=-128, le=127),), nw.Int8()),
        ((Interval(ge=0, le=255),), nw.UInt8()),
        ((Interval(ge=-32768, le=32767),), nw.Int16()),
        ((Interval(ge=0, le=65535),), nw.UInt16()),
        ((Ge(0), Le(100)), nw.UInt8()),
        ((Gt(-1), Lt(100)), nw.UInt8()),
        ((Ge(10), Le(50)), nw.UInt8()),
        ((Ge(0), Ge(10)), nw.UInt64()),
        ((Ge(0), Le(255)), nw.UInt8()),
        ((Ge(0), Le(256)), nw.UInt16()),
        ((Ge(0), Le(65536)), nw.UInt32()),
        ((Ge(0), Le(4294967296)), nw.UInt64()),
        ((Ge(-128), Le(127)), nw.Int8()),
        ((Ge(-129), Le(127)), nw.Int16()),
        ((Ge(-32769), Le(32767)), nw.Int32()),
        ((Ge(-2147483649), Le(2147483647)), nw.Int64()),
    ],
)
def test_int_with_constraint(
    annotated_types_parser: AnnotatedTypesParser, metadata: tuple, expected: nw.dtypes.DType
) -> None:
    result = annotated_types_parser.parse(int, metadata)
    assert result == expected


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        (42, 42),
        (3.14, 3.14),
        ("123", 123),
        ("3.14", 3.14),
    ],
)
def test_extract_value(annotated_types_parser: AnnotatedTypesParser, input_value: Any, expected: float) -> None:
    result = annotated_types_parser._extract_numeric_value(input_value)
    assert result == expected


@pytest.mark.parametrize("input_value", [None, {"key": "value"}])
def test_extract_value_raise(annotated_types_parser: AnnotatedTypesParser, input_value: Any) -> None:
    with pytest.raises(TypeError, match=r"Cannot .* value"):
        annotated_types_parser._extract_numeric_value(input_value)


@given(lb=st.integers(-128, -1), ub=st.integers(1, 127))
def test_parse_to_int8_hypothesis(annotated_types_parser: AnnotatedTypesParser, lb: int, ub: int) -> None:
    result = annotated_types_parser.parse(int, metadata=(Ge(lb), Le(ub)))
    assert result == nw.Int8()


@given(ub=st.integers(1, 255))
def test_parse_to_uint8_hypothesis(annotated_types_parser: AnnotatedTypesParser, ub: int) -> None:
    result = annotated_types_parser.parse(int, metadata=(Ge(0), Le(ub)))
    assert result == nw.UInt8()


@given(lb=st.integers(-32768, -129), ub=st.integers(129, 32767))
def test_parse_to_int16_hypothesis(annotated_types_parser: AnnotatedTypesParser, lb: int, ub: int) -> None:
    result = annotated_types_parser.parse(int, metadata=(Ge(lb), Le(ub)))
    assert result == nw.Int16()


@given(ub=st.integers(257, 65535))
def test_parse_to_uint16_hypothesis(annotated_types_parser: AnnotatedTypesParser, ub: int) -> None:
    result = annotated_types_parser.parse(int, metadata=(Ge(0), Le(ub)))
    assert result == nw.UInt16()


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ((Gt(0),), nw.UInt64()),
        ((Ge(0),), nw.UInt64()),
        ((Gt(-1),), nw.UInt64()),
        ((Ge(-128), Le(127)), nw.Int8()),
        ((Ge(0), Le(255)), nw.UInt8()),
        ((Ge(-32768), Le(32767)), nw.Int16()),
        ((Ge(0), Le(65535)), nw.UInt16()),
        ((Interval(ge=0, le=100),), nw.UInt8()),
        ((Interval(ge=-100, le=100),), nw.Int8()),
    ],
)
def test_parse_integer_constraints_parametrized(
    annotated_types_parser: AnnotatedTypesParser, metadata: tuple, expected: nw.dtypes.DType
) -> None:
    result = annotated_types_parser.parse(int, metadata=metadata)
    assert result == expected
