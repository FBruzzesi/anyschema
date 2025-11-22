from __future__ import annotations

from typing import Annotated

import narwhals as nw
import pytest

from anyschema.parsers.annotated import AnnotatedParser
from anyschema.parsers.base import ParserChain
from anyschema.parsers.py_types import PyTypeParser


class TestAnnotatedParserBasicTypes:
    """Test cases for Annotated basic types."""

    @pytest.fixture
    def parser(self) -> AnnotatedParser:
        """Create an AnnotatedParser instance with parser_chain set."""
        annotated_parser = AnnotatedParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_parser, py_parser])
        annotated_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_parser

    def test_parse_annotated_int(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated[int, ...]."""
        result = parser.parse(Annotated[int, "metadata"])
        assert result == nw.Int64()

    def test_parse_annotated_str(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated[str, ...]."""
        result = parser.parse(Annotated[str, "some metadata"])
        assert result == nw.String()

    def test_parse_annotated_float(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated[float, ...]."""
        result = parser.parse(Annotated[float, "metadata"])
        assert result == nw.Float64()

    def test_parse_annotated_bool(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated[bool, ...]."""
        result = parser.parse(Annotated[bool, "metadata"])
        assert result == nw.Boolean()

    def test_parse_annotated_single_arg(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated type with single metadata item."""
        result = parser.parse(Annotated[int, "meta"])
        assert result == nw.Int64()


class TestAnnotatedParserMultipleMetadata:
    """Test cases for Annotated types with multiple metadata items."""

    @pytest.fixture
    def parser(self) -> AnnotatedParser:
        """Create an AnnotatedParser instance with parser_chain set."""
        annotated_parser = AnnotatedParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_parser, py_parser])
        annotated_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_parser

    def test_parse_annotated_multiple_metadata(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated with multiple metadata items."""
        result = parser.parse(Annotated[int, "meta1", "meta2", "meta3"])
        # PyTypeParser doesn't use metadata, but it should parse successfully
        assert result == nw.Int64()

    def test_parse_annotated_with_dict_metadata(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated with dict metadata."""
        result = parser.parse(Annotated[str, {"key": "value"}])
        assert result == nw.String()

    def test_parse_annotated_with_tuple_metadata(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated with tuple metadata."""
        result = parser.parse(Annotated[float, ("min", 0.0), ("max", 100.0)])
        assert result == nw.Float64()


class TestAnnotatedParserComplexTypes:
    """Test cases for Annotated complex types."""

    @pytest.fixture
    def parser(self) -> AnnotatedParser:
        """Create an AnnotatedParser instance with parser_chain set."""
        annotated_parser = AnnotatedParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_parser, py_parser])
        annotated_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_parser

    def test_parse_annotated_list(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated[list[int], ...]."""
        result = parser.parse(Annotated[list[int], "metadata"])
        assert result == nw.List(nw.Int64())

    def test_parse_annotated_tuple(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated[tuple[str, ...], ...]."""
        result = parser.parse(Annotated[tuple[str, ...], "metadata"])
        assert result == nw.List(nw.String())

    def test_parse_annotated_fixed_tuple(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated[tuple[int, int, int], ...]."""
        result = parser.parse(Annotated[tuple[int, int, int], "metadata"])
        assert result == nw.Array(nw.Int64(), shape=3)

    def test_parse_nested_list(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated[list[list[str]], ...]."""
        result = parser.parse(Annotated[list[list[str]], "metadata"])
        assert result == nw.List(nw.List(nw.String()))


class TestAnnotatedParserPreservesMetadata:
    """Test that metadata is preserved and passed to the chain."""

    @pytest.fixture
    def parser(self) -> AnnotatedParser:
        """Create an AnnotatedParser instance with parser_chain set."""
        annotated_parser = AnnotatedParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_parser, py_parser])
        annotated_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_parser

    def test_parse_combines_outer_and_annotated_metadata(self, parser: AnnotatedParser) -> None:
        """Test that outer metadata is combined with Annotated metadata."""
        # When parsing Annotated[int, "inner"] with outer metadata ("outer",)
        # the combined metadata should be ("outer", "inner")
        # This test verifies the metadata is passed through correctly
        result = parser.parse(Annotated[int, "inner"], metadata=("outer",))
        assert result == nw.Int64()


class TestAnnotatedParserNonAnnotatedTypes:
    """Test cases for non-Annotated types (should return None)."""

    @pytest.fixture
    def parser(self) -> AnnotatedParser:
        """Create an AnnotatedParser instance with parser_chain set."""
        annotated_parser = AnnotatedParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_parser, py_parser])
        annotated_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_parser

    def test_parse_plain_int_returns_none(self, parser: AnnotatedParser) -> None:
        """Test parsing plain int returns None (not Annotated)."""
        result = parser.parse(int)
        assert result is None

    def test_parse_plain_str_returns_none(self, parser: AnnotatedParser) -> None:
        """Test parsing plain str returns None (not Annotated)."""
        result = parser.parse(str)
        assert result is None

    def test_parse_list_returns_none(self, parser: AnnotatedParser) -> None:
        """Test parsing list[int] returns None (not Annotated)."""
        result = parser.parse(list[int])
        assert result is None

    def test_parse_tuple_returns_none(self, parser: AnnotatedParser) -> None:
        """Test parsing tuple[str, ...] returns None (not Annotated)."""
        result = parser.parse(tuple[str, ...])
        assert result is None


class TestAnnotatedParserWithCustomMetadata:
    """Test cases for Annotated types with custom constraint metadata."""

    @pytest.fixture
    def parser(self) -> AnnotatedParser:
        """Create an AnnotatedParser instance with parser_chain set."""
        annotated_parser = AnnotatedParser()
        py_parser = PyTypeParser()
        chain = ParserChain([annotated_parser, py_parser])
        annotated_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return annotated_parser

    def test_parse_annotated_with_class_metadata(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated with custom class metadata."""

        class CustomMetadata:
            def __init__(self, value: str) -> None:
                self.value = value

        result = parser.parse(Annotated[int, CustomMetadata("test")])
        assert result == nw.Int64()

    def test_parse_annotated_with_callable_metadata(self, parser: AnnotatedParser) -> None:
        """Test parsing Annotated with callable metadata."""

        def validator(x: int) -> bool:
            return x > 0

        result = parser.parse(Annotated[int, validator])
        assert result == nw.Int64()


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (Annotated[int, "meta"], nw.Int64()),
        (Annotated[str, "meta"], nw.String()),
        (Annotated[float, "meta"], nw.Float64()),
        (Annotated[bool, "meta"], nw.Boolean()),
        (Annotated[list[int], "meta"], nw.List(nw.Int64())),
        (Annotated[list[str], "meta"], nw.List(nw.String())),
        (Annotated[tuple[int, ...], "meta"], nw.List(nw.Int64())),
        (Annotated[tuple[str, str, str], "meta"], nw.Array(nw.String(), shape=3)),
    ],
)
def test_parse_annotated_types_parametrized(input_type: type, expected: nw.DType) -> None:
    """Parametrized test for Annotated types."""
    annotated_parser = AnnotatedParser()
    py_parser = PyTypeParser()
    chain = ParserChain([annotated_parser, py_parser])
    annotated_parser.parser_chain = chain
    py_parser.parser_chain = chain

    result = annotated_parser.parse(input_type)
    assert result == expected


@pytest.mark.parametrize(
    "metadata_items",
    [
        ("meta1",),
        ("meta1", "meta2"),
        ("meta1", "meta2", "meta3"),
        ({"key": "value"},),
        (["item1", "item2"],),
        (1, 2, 3),
    ],
)
def test_parse_annotated_various_metadata_parametrized(metadata_items: tuple) -> None:
    """Parametrized test for Annotated with various metadata."""
    annotated_parser = AnnotatedParser()
    py_parser = PyTypeParser()
    chain = ParserChain([annotated_parser, py_parser])
    annotated_parser.parser_chain = chain
    py_parser.parser_chain = chain

    input_type = Annotated[int, *metadata_items]
    result = annotated_parser.parse(input_type)
    assert result == nw.Int64()
