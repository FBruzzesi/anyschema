from __future__ import annotations

import hypothesis.strategies as st
import narwhals as nw
import pytest
from annotated_types import Ge, Gt, Interval, Le, Lt
from hypothesis import given

from anyschema.parsers._base import ParserChain
from anyschema.parsers._builtin import PyTypeParser
from anyschema.parsers.annotated_types import AnnotatedTypesParser


class TestAnnotatedTypesParserNoMetadata:
    """Test cases for types without metadata."""

    @pytest.fixture
    def parser(self) -> AnnotatedTypesParser:
        """Create an AnnotatedTypesParser instance with parser_chain set."""
        annotated_types_parser = AnnotatedTypesParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_types_parser, py_parser])
        annotated_types_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_types_parser

    def test_parse_int_no_metadata_returns_none(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int without metadata returns None."""
        result = parser.parse(int)
        assert result is None

    def test_parse_str_returns_none(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing str returns None (not handled)."""
        result = parser.parse(str, metadata=("meta",))
        assert result is None

    def test_parse_float_returns_none(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing float returns None (not handled)."""
        result = parser.parse(float, metadata=("meta",))
        assert result is None


class TestAnnotatedTypesParserGtConstraint:
    """Test cases for Gt (greater than) constraint."""

    @pytest.fixture
    def parser(self) -> AnnotatedTypesParser:
        """Create an AnnotatedTypesParser instance with parser_chain set."""
        annotated_types_parser = AnnotatedTypesParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_types_parser, py_parser])
        annotated_types_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_types_parser

    def test_parse_int_gt_zero(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Gt(0) constraint."""
        result = parser.parse(int, metadata=(Gt(0),))
        assert result == nw.UInt64()

    def test_parse_int_gt_minus_one(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Gt(-1) constraint."""
        result = parser.parse(int, metadata=(Gt(-1),))
        assert result == nw.UInt64()

    def test_parse_int_gt_negative(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Gt(-100) constraint."""
        result = parser.parse(int, metadata=(Gt(-100),))
        # Lower bound is -99, which is negative, so Int64
        assert result == nw.Int64()

    def test_parse_int_gt_large_positive(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with large Gt constraint."""
        result = parser.parse(int, metadata=(Gt(1000),))
        assert result == nw.UInt64()


class TestAnnotatedTypesParserGeConstraint:
    """Test cases for Ge (greater than or equal) constraint."""

    @pytest.fixture
    def parser(self) -> AnnotatedTypesParser:
        """Create an AnnotatedTypesParser instance with parser_chain set."""
        annotated_types_parser = AnnotatedTypesParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_types_parser, py_parser])
        annotated_types_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_types_parser

    def test_parse_int_ge_zero(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Ge(0) constraint."""
        result = parser.parse(int, metadata=(Ge(0),))
        assert result == nw.UInt64()

    def test_parse_int_ge_one(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Ge(1) constraint."""
        result = parser.parse(int, metadata=(Ge(1),))
        assert result == nw.UInt64()

    def test_parse_int_ge_negative(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Ge(-100) constraint."""
        result = parser.parse(int, metadata=(Ge(-100),))
        # Lower bound is -100, which is negative, so Int64
        assert result == nw.Int64()


class TestAnnotatedTypesParserLtConstraint:
    """Test cases for Lt (less than) constraint."""

    @pytest.fixture
    def parser(self) -> AnnotatedTypesParser:
        """Create an AnnotatedTypesParser instance with parser_chain set."""
        annotated_types_parser = AnnotatedTypesParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_types_parser, py_parser])
        annotated_types_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_types_parser

    def test_parse_int_lt_ten(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Lt(10) constraint."""
        result = parser.parse(int, metadata=(Lt(10),))
        # Range is MIN_INT to 9, which includes negatives, so Int64
        assert result == nw.Int64()

    def test_parse_int_lt_negative(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Lt(-100) constraint."""
        result = parser.parse(int, metadata=(Lt(-100),))
        # Upper bound is -101, which is negative, so Int64
        assert result == nw.Int64()


class TestAnnotatedTypesParserLeConstraint:
    """Test cases for Le (less than or equal) constraint."""

    @pytest.fixture
    def parser(self) -> AnnotatedTypesParser:
        """Create an AnnotatedTypesParser instance with parser_chain set."""
        annotated_types_parser = AnnotatedTypesParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_types_parser, py_parser])
        annotated_types_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_types_parser

    def test_parse_int_le_ten(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Le(10) constraint."""
        result = parser.parse(int, metadata=(Le(10),))
        # Range is MIN_INT to 10, which includes negatives, so Int64
        assert result == nw.Int64()

    def test_parse_int_le_negative(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Le(-100) constraint."""
        result = parser.parse(int, metadata=(Le(-100),))
        # Upper bound is -100, which is negative, so Int64
        assert result == nw.Int64()


class TestAnnotatedTypesParserIntervalConstraint:
    """Test cases for Interval constraint."""

    @pytest.fixture
    def parser(self) -> AnnotatedTypesParser:
        """Create an AnnotatedTypesParser instance with parser_chain set."""
        annotated_types_parser = AnnotatedTypesParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_types_parser, py_parser])
        annotated_types_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_types_parser

    def test_parse_int_interval_ge_le(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Interval(ge=0, le=100)."""
        result = parser.parse(int, metadata=(Interval(ge=0, le=100),))
        assert result == nw.UInt8()

    def test_parse_int_interval_gt_lt(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Interval(gt=0, lt=100)."""
        result = parser.parse(int, metadata=(Interval(gt=0, lt=100),))
        assert result == nw.UInt8()

    def test_parse_int_interval_negative_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with negative range."""
        result = parser.parse(int, metadata=(Interval(ge=-100, le=100),))
        assert result == nw.Int8()

    def test_parse_int_interval_int8_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Int8 range."""
        result = parser.parse(int, metadata=(Interval(ge=-128, le=127),))
        assert result == nw.Int8()

    def test_parse_int_interval_uint8_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with UInt8 range."""
        result = parser.parse(int, metadata=(Interval(ge=0, le=255),))
        assert result == nw.UInt8()

    def test_parse_int_interval_int16_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Int16 range."""
        result = parser.parse(int, metadata=(Interval(ge=-32768, le=32767),))
        assert result == nw.Int16()

    def test_parse_int_interval_uint16_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with UInt16 range."""
        result = parser.parse(int, metadata=(Interval(ge=0, le=65535),))
        assert result == nw.UInt16()


class TestAnnotatedTypesParserCombinedConstraints:
    """Test cases for combined constraints."""

    @pytest.fixture
    def parser(self) -> AnnotatedTypesParser:
        """Create an AnnotatedTypesParser instance with parser_chain set."""
        annotated_types_parser = AnnotatedTypesParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_types_parser, py_parser])
        annotated_types_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_types_parser

    def test_parse_int_ge_and_le(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with both Ge and Le constraints."""
        result = parser.parse(int, metadata=(Ge(0), Le(100)))
        assert result == nw.UInt8()

    def test_parse_int_gt_and_lt(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with both Gt and Lt constraints."""
        result = parser.parse(int, metadata=(Gt(-1), Lt(100)))
        assert result == nw.UInt8()

    def test_parse_int_multiple_constraints_narrowing(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with multiple constraints that narrow the range."""
        # Ge(10) sets lower bound to 10
        # Le(50) sets upper bound to 50
        result = parser.parse(int, metadata=(Ge(10), Le(50)))
        assert result == nw.UInt8()

    def test_parse_int_conflicting_constraints(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with overlapping constraints (most restrictive wins)."""
        # Ge(0) and Ge(10) - Ge(10) is more restrictive
        result = parser.parse(int, metadata=(Ge(0), Ge(10)))
        assert result == nw.UInt64()


class TestAnnotatedTypesParserUnsignedIntegerRanges:
    """Test cases for unsigned integer ranges."""

    @pytest.fixture
    def parser(self) -> AnnotatedTypesParser:
        """Create an AnnotatedTypesParser instance with parser_chain set."""
        annotated_types_parser = AnnotatedTypesParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_types_parser, py_parser])
        annotated_types_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_types_parser

    def test_parse_uint8_max(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with UInt8 max value."""
        result = parser.parse(int, metadata=(Ge(0), Le(255)))
        assert result == nw.UInt8()

    def test_parse_uint16_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int that requires UInt16."""
        result = parser.parse(int, metadata=(Ge(0), Le(256)))
        assert result == nw.UInt16()

    def test_parse_uint32_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int that requires UInt32."""
        result = parser.parse(int, metadata=(Ge(0), Le(65536)))
        assert result == nw.UInt32()

    def test_parse_uint64_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int that requires UInt64."""
        result = parser.parse(int, metadata=(Ge(0), Le(4294967296)))
        assert result == nw.UInt64()


class TestAnnotatedTypesParserSignedIntegerRanges:
    """Test cases for signed integer ranges."""

    @pytest.fixture
    def parser(self) -> AnnotatedTypesParser:
        """Create an AnnotatedTypesParser instance with parser_chain set."""
        annotated_types_parser = AnnotatedTypesParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_types_parser, py_parser])
        annotated_types_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_types_parser

    def test_parse_int8_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int with Int8 range."""
        result = parser.parse(int, metadata=(Ge(-128), Le(127)))
        assert result == nw.Int8()

    def test_parse_int16_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int that requires Int16."""
        result = parser.parse(int, metadata=(Ge(-129), Le(127)))
        assert result == nw.Int16()

    def test_parse_int32_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int that requires Int32."""
        result = parser.parse(int, metadata=(Ge(-32769), Le(32767)))
        assert result == nw.Int32()

    def test_parse_int64_range(self, parser: AnnotatedTypesParser) -> None:
        """Test parsing int that requires Int64."""
        result = parser.parse(int, metadata=(Ge(-2147483649), Le(2147483647)))
        assert result == nw.Int64()


class TestAnnotatedTypesParserExtractNumericValue:
    """Test cases for _extract_numeric_value method."""

    @pytest.fixture
    def parser(self) -> AnnotatedTypesParser:
        """Create an AnnotatedTypesParser instance."""
        return AnnotatedTypesParser()

    def test_extract_int(self, parser: AnnotatedTypesParser) -> None:
        """Test extracting int value."""
        result = parser._extract_numeric_value(42)
        assert result == 42

    def test_extract_float(self, parser: AnnotatedTypesParser) -> None:
        """Test extracting float value."""
        result = parser._extract_numeric_value(3.14)
        assert result == 3.14

    def test_extract_from_string_int(self, parser: AnnotatedTypesParser) -> None:
        """Test extracting numeric value from string."""
        result = parser._extract_numeric_value("123")
        assert result == 123

    def test_extract_from_string_float(self, parser: AnnotatedTypesParser) -> None:
        """Test extracting float value from string."""
        result = parser._extract_numeric_value("3.14")
        assert result == 3.14

    def test_extract_none_raises(self, parser: AnnotatedTypesParser) -> None:
        """Test extracting from None raises TypeError."""
        with pytest.raises(TypeError, match="Cannot extract numeric value from None"):
            parser._extract_numeric_value(None)

    def test_extract_invalid_type_raises(self, parser: AnnotatedTypesParser) -> None:
        """Test extracting from invalid type raises TypeError."""
        with pytest.raises(TypeError, match="Cannot convert .* to numeric value"):
            parser._extract_numeric_value({"key": "value"})


@given(lb=st.integers(-128, -1), ub=st.integers(1, 127))
def test_parse_to_int8_hypothesis(lb: int, ub: int) -> None:
    """Hypothesis test for Int8 range."""
    parser = AnnotatedTypesParser()
    py_parser = PyTypeParser()
    chain = ParserChain([parser, py_parser])
    parser.parser_chain = chain
    py_parser.parser_chain = chain

    result = parser.parse(int, metadata=(Ge(lb), Le(ub)))
    assert result == nw.Int8()


@given(ub=st.integers(1, 255))
def test_parse_to_uint8_hypothesis(ub: int) -> None:
    """Hypothesis test for UInt8 range."""
    parser = AnnotatedTypesParser()
    py_parser = PyTypeParser()
    chain = ParserChain([parser, py_parser])
    parser.parser_chain = chain
    py_parser.parser_chain = chain

    result = parser.parse(int, metadata=(Ge(0), Le(ub)))
    assert result == nw.UInt8()


@given(lb=st.integers(-32768, -129), ub=st.integers(129, 32767))
def test_parse_to_int16_hypothesis(lb: int, ub: int) -> None:
    """Hypothesis test for Int16 range."""
    parser = AnnotatedTypesParser()
    py_parser = PyTypeParser()
    chain = ParserChain([parser, py_parser])
    parser.parser_chain = chain
    py_parser.parser_chain = chain

    result = parser.parse(int, metadata=(Ge(lb), Le(ub)))
    assert result == nw.Int16()


@given(ub=st.integers(257, 65535))
def test_parse_to_uint16_hypothesis(ub: int) -> None:
    """Hypothesis test for UInt16 range."""
    parser = AnnotatedTypesParser()
    py_parser = PyTypeParser()
    chain = ParserChain([parser, py_parser])
    parser.parser_chain = chain
    py_parser.parser_chain = chain

    result = parser.parse(int, metadata=(Ge(0), Le(ub)))
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
def test_parse_integer_constraints_parametrized(metadata: tuple, expected: nw.DType) -> None:
    """Parametrized test for integer constraints."""
    parser = AnnotatedTypesParser()
    py_parser = PyTypeParser()
    chain = ParserChain([parser, py_parser])
    parser.parser_chain = chain
    py_parser.parser_chain = chain

    result = parser.parse(int, metadata=metadata)
    assert result == expected
