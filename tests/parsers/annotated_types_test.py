from __future__ import annotations

from typing import TYPE_CHECKING, Any

import hypothesis.strategies as st
import narwhals as nw
import pytest
from annotated_types import Ge, Gt, Interval, Le, Lt
from hypothesis import given

from anyschema.parsers import ParserPipeline
from anyschema.parsers._builtin import PyTypeStep
from anyschema.parsers.annotated_types import AnnotatedTypesStep

if TYPE_CHECKING:
    from anyschema.typing import FieldConstraints


@pytest.fixture(scope="module")
def annotated_types_parser() -> AnnotatedTypesStep:
    """Create an AnnotatedTypesStep instance with pipeline set."""
    annotated_types_parser = AnnotatedTypesStep()
    py_parser = PyTypeStep()
    chain = ParserPipeline([annotated_types_parser, py_parser])
    annotated_types_parser.pipeline = chain
    py_parser.pipeline = chain
    return annotated_types_parser


@pytest.mark.parametrize("input_type", [int, str, float, list[int]])
def test_parse_non_annotated(annotated_types_parser: AnnotatedTypesStep, input_type: type) -> None:
    result = annotated_types_parser.parse(input_type, (), {})
    assert result is None


@pytest.mark.parametrize(
    ("constraints", "expected"),
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
    annotated_types_parser: AnnotatedTypesStep, constraints: FieldConstraints, expected: nw.dtypes.DType
) -> None:
    result = annotated_types_parser.parse(int, constraints=constraints, metadata={})
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
def test_extract_value(annotated_types_parser: AnnotatedTypesStep, input_value: Any, expected: float) -> None:
    result = annotated_types_parser._extract_numeric_value(input_value)
    assert result == expected


@pytest.mark.parametrize("input_value", [None, {"key": "value"}])
def test_extract_value_raise(annotated_types_parser: AnnotatedTypesStep, input_value: Any) -> None:
    with pytest.raises(TypeError, match=r"Cannot .* value"):
        annotated_types_parser._extract_numeric_value(input_value)


@given(lb=st.integers(-128, -1), ub=st.integers(1, 127))
def test_parse_to_int8_hypothesis(annotated_types_parser: AnnotatedTypesStep, lb: int, ub: int) -> None:
    result = annotated_types_parser.parse(int, constraints=(Ge(lb), Le(ub)), metadata={})
    assert result == nw.Int8()


@given(ub=st.integers(1, 255))
def test_parse_to_uint8_hypothesis(annotated_types_parser: AnnotatedTypesStep, ub: int) -> None:
    result = annotated_types_parser.parse(int, constraints=(Ge(0), Le(ub)), metadata={})
    assert result == nw.UInt8()


@given(lb=st.integers(-32768, -129), ub=st.integers(129, 32767))
def test_parse_to_int16_hypothesis(annotated_types_parser: AnnotatedTypesStep, lb: int, ub: int) -> None:
    result = annotated_types_parser.parse(int, constraints=(Ge(lb), Le(ub)), metadata={})
    assert result == nw.Int16()


@given(ub=st.integers(257, 65535))
def test_parse_to_uint16_hypothesis(annotated_types_parser: AnnotatedTypesStep, ub: int) -> None:
    result = annotated_types_parser.parse(int, constraints=(Ge(0), Le(ub)), metadata={})
    assert result == nw.UInt16()


@pytest.mark.parametrize(
    ("constraints", "expected"),
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
    annotated_types_parser: AnnotatedTypesStep, constraints: FieldConstraints, expected: nw.dtypes.DType
) -> None:
    result = annotated_types_parser.parse(int, constraints=constraints, metadata={})
    assert result == expected


def test_parse_int_exceeding_uint64_max(annotated_types_parser: AnnotatedTypesStep) -> None:
    """Test that upper bounds exceeding UInt64 max still return UInt64."""
    # UInt64 max is 18446744073709551615
    huge_upper_bound = 18446744073709551616 * 2  # Way larger than UInt64 max
    result = annotated_types_parser.parse(int, constraints=(Ge(0), Le(huge_upper_bound)), metadata={})
    assert result == nw.UInt64()


def test_parse_int_exceeding_int64_max(annotated_types_parser: AnnotatedTypesStep) -> None:
    """Test that ranges exceeding Int64 max still return Int64."""
    # Int64 range is -9223372036854775808 to 9223372036854775807
    result = annotated_types_parser.parse(int, constraints=(Ge(0),), metadata={})
    # With Ge(0), lower_bound=0 (non-negative), so it goes to unsigned path
    # But with no upper bound constraint, upper_bound stays at MAX_INT
    # which is way larger than any UInt type max, so it should... wait
    # Actually UInt64 max IS MAX_INT, so it should match and return UInt64
    assert result == nw.UInt64()


def test_parse_int_with_very_negative_lower_bound(annotated_types_parser: AnnotatedTypesStep) -> None:
    """Test fallback to Int64 when no specific signed integer type fits."""
    # Start with a negative lower bound (so we use signed integers)
    # but no upper bound constraint (upper_bound stays at MAX_INT = UInt64 max)
    # This means no Int type will fit (all require upper_bound <= their max)
    result = annotated_types_parser.parse(int, constraints=(Ge(-100),), metadata={})
    # With only Ge(-100), upper_bound stays at MAX_INT which exceeds all Int ranges
    assert result == nw.Int64()
