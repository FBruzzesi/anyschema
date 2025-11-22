from __future__ import annotations

from typing import ForwardRef, Optional

import narwhals as nw
import pytest

from anyschema.parsers.base import ParserChain
from anyschema.parsers.forward_ref import ForwardRefParser
from anyschema.parsers.py_types import PyTypeParser


class TestForwardRefParserBasicTypes:
    """Test cases for ForwardRef basic types."""

    @pytest.fixture
    def parser(self) -> ForwardRefParser:
        """Create a ForwardRefParser instance with parser_chain set."""
        forward_ref_parser = ForwardRefParser()
        py_parser = PyTypeParser()
        chain = ParserChain([forward_ref_parser, py_parser])
        forward_ref_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return forward_ref_parser

    def test_parse_forward_ref_int(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef('int')."""
        result = parser.parse(ForwardRef("int"))
        assert result == nw.Int64()

    def test_parse_forward_ref_str(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef('str')."""
        result = parser.parse(ForwardRef("str"))
        assert result == nw.String()

    def test_parse_forward_ref_float(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef('float')."""
        result = parser.parse(ForwardRef("float"))
        assert result == nw.Float64()

    def test_parse_forward_ref_bool(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef('bool')."""
        result = parser.parse(ForwardRef("bool"))
        assert result == nw.Boolean()


class TestForwardRefParserGenericTypes:
    """Test cases for ForwardRef generic types."""

    @pytest.fixture
    def parser(self) -> ForwardRefParser:
        """Create a ForwardRefParser instance with parser_chain set."""
        forward_ref_parser = ForwardRefParser()
        py_parser = PyTypeParser()
        chain = ParserChain([forward_ref_parser, py_parser])
        forward_ref_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return forward_ref_parser

    def test_parse_forward_ref_list_int(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef('list[int]')."""
        result = parser.parse(ForwardRef("list[int]"))
        assert result == nw.List(nw.Int64())

    def test_parse_forward_ref_list_str(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef('list[str]')."""
        result = parser.parse(ForwardRef("list[str]"))
        assert result == nw.List(nw.String())

    def test_parse_forward_ref_tuple_ellipsis(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef('tuple[int, ...]')."""
        result = parser.parse(ForwardRef("tuple[int, ...]"))
        assert result == nw.List(nw.Int64())

    def test_parse_forward_ref_list_capital(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef('List[int]') with typing.List."""
        result = parser.parse(ForwardRef("List[int]"))
        assert result == nw.List(nw.Int64())

    def test_parse_forward_ref_union_type(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef with union type."""
        # Need to use a parser chain that includes UnionTypeParser for this to work
        from anyschema.parsers.union_types import UnionTypeParser

        union_parser = UnionTypeParser()
        py_parser = PyTypeParser()
        forward_ref_parser = ForwardRefParser()
        from anyschema.parsers.base import ParserChain

        chain = ParserChain([forward_ref_parser, union_parser, py_parser])
        forward_ref_parser.parser_chain = chain
        union_parser.parser_chain = chain
        py_parser.parser_chain = chain

        result = forward_ref_parser.parse(ForwardRef("int | None"))
        assert result == nw.Int64()


class TestForwardRefParserCustomNamespace:
    """Test cases for ForwardRef with custom namespace."""

    def test_parse_forward_ref_custom_class(self) -> None:
        """Test parsing ForwardRef to custom class with custom namespace."""

        class CustomClass:
            pass

        custom_globals = {"CustomClass": CustomClass}
        forward_ref_parser = ForwardRefParser(globalns=custom_globals)
        py_parser = PyTypeParser()
        chain = ParserChain([forward_ref_parser, py_parser])
        forward_ref_parser.parser_chain = chain
        py_parser.parser_chain = chain

        # CustomClass is not handled by PyTypeParser, so should raise NotImplementedError
        with pytest.raises(NotImplementedError, match="No parser in chain could handle type"):
            forward_ref_parser.parse(ForwardRef("CustomClass"))

    def test_parse_forward_ref_override_builtin(self) -> None:
        """Test parsing ForwardRef with overridden builtin type."""
        # Override 'int' in global namespace to return something else
        # This is contrived but tests namespace priority
        custom_globals = {"int": str}
        forward_ref_parser = ForwardRefParser(globalns=custom_globals)
        py_parser = PyTypeParser()
        chain = ParserChain([forward_ref_parser, py_parser])
        forward_ref_parser.parser_chain = chain
        py_parser.parser_chain = chain

        result = forward_ref_parser.parse(ForwardRef("int"))
        # 'int' resolves to str due to override
        assert result == nw.String()

    def test_parse_forward_ref_local_namespace(self) -> None:
        """Test parsing ForwardRef with local namespace."""

        class LocalClass:
            pass

        forward_ref_parser = ForwardRefParser(localns={"LocalClass": int})
        py_parser = PyTypeParser()
        chain = ParserChain([forward_ref_parser, py_parser])
        forward_ref_parser.parser_chain = chain
        py_parser.parser_chain = chain

        result = forward_ref_parser.parse(ForwardRef("LocalClass"))
        assert result == nw.Int64()


class TestForwardRefParserNonForwardRefTypes:
    """Test cases for non-ForwardRef types (should return None)."""

    @pytest.fixture
    def parser(self) -> ForwardRefParser:
        """Create a ForwardRefParser instance with parser_chain set."""
        forward_ref_parser = ForwardRefParser()
        py_parser = PyTypeParser()
        chain = ParserChain([forward_ref_parser, py_parser])
        forward_ref_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return forward_ref_parser

    def test_parse_plain_int_returns_none(self, parser: ForwardRefParser) -> None:
        """Test parsing plain int returns None (not a ForwardRef)."""
        result = parser.parse(int)
        assert result is None

    def test_parse_plain_str_returns_none(self, parser: ForwardRefParser) -> None:
        """Test parsing plain str returns None (not a ForwardRef)."""
        result = parser.parse(str)
        assert result is None

    def test_parse_list_returns_none(self, parser: ForwardRefParser) -> None:
        """Test parsing list[int] returns None (not a ForwardRef)."""
        result = parser.parse(list[int])
        assert result is None


class TestForwardRefParserResolutionErrors:
    """Test cases for ForwardRef resolution errors."""

    @pytest.fixture
    def parser(self) -> ForwardRefParser:
        """Create a ForwardRefParser instance with parser_chain set."""
        forward_ref_parser = ForwardRefParser()
        py_parser = PyTypeParser()
        chain = ParserChain([forward_ref_parser, py_parser])
        forward_ref_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return forward_ref_parser

    def test_parse_forward_ref_undefined_raises(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef to undefined type raises."""
        with pytest.raises(NotImplementedError, match="Failed to resolve ForwardRef"):
            parser.parse(ForwardRef("UndefinedType"))

    def test_parse_forward_ref_invalid_syntax_raises(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef with invalid syntax raises."""
        # ForwardRef constructor itself raises SyntaxError for invalid syntax
        with pytest.raises(SyntaxError, match="Forward reference must be an expression"):
            ForwardRef("list[")

    def test_parse_forward_ref_invalid_expression_raises(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef with invalid expression raises."""
        # '1 + 1' evaluates to 2, which isn't a type the parser can handle
        with pytest.raises(NotImplementedError, match="No parser in chain could handle type"):
            parser.parse(ForwardRef("1 + 1"))


class TestForwardRefParserWithMetadata:
    """Test cases for ForwardRef with metadata."""

    @pytest.fixture
    def parser(self) -> ForwardRefParser:
        """Create a ForwardRefParser instance with parser_chain set."""
        forward_ref_parser = ForwardRefParser()
        py_parser = PyTypeParser()
        chain = ParserChain([forward_ref_parser, py_parser])
        forward_ref_parser.parser_chain = chain
        py_parser.parser_chain = chain
        return forward_ref_parser

    def test_parse_forward_ref_with_metadata(self, parser: ForwardRefParser) -> None:
        """Test parsing ForwardRef with metadata (metadata is passed through)."""
        result = parser.parse(ForwardRef("int"), metadata=("some", "metadata"))
        # Metadata is passed to the chain but PyTypeParser doesn't use it
        assert result == nw.Int64()


class TestForwardRefParserBuildNamespace:
    """Test cases for _build_namespace method."""

    def test_build_namespace_default(self) -> None:
        """Test building namespace with default values."""
        parser = ForwardRefParser()

        # Check that common types are in the namespace
        assert parser.globalns["int"] is int
        assert parser.globalns["str"] is str
        assert parser.globalns["float"] is float
        assert parser.globalns["bool"] is bool
        assert parser.globalns["list"] is list
        assert "Optional" in parser.globalns
        assert "Union" in parser.globalns
        assert "List" in parser.globalns

    def test_build_namespace_with_custom(self) -> None:
        """Test building namespace with custom globals."""

        class CustomType:
            pass

        custom_globals = {"CustomType": CustomType, "MyInt": int}
        parser = ForwardRefParser(globalns=custom_globals)

        # Check that custom types are in the namespace
        assert parser.globalns["CustomType"] is CustomType
        assert parser.globalns["MyInt"] is int
        # Built-ins should still be there
        assert parser.globalns["int"] is int
        assert parser.globalns["str"] is str

    def test_build_namespace_override(self) -> None:
        """Test that custom globals can override built-ins."""
        custom_globals = {"int": str}
        parser = ForwardRefParser(globalns=custom_globals)

        # Custom override should win
        assert parser.globalns["int"] is str

    def test_local_namespace_default(self) -> None:
        """Test that local namespace defaults to empty dict."""
        parser = ForwardRefParser()
        assert parser.localns == {}

    def test_local_namespace_custom(self) -> None:
        """Test setting custom local namespace."""
        localns = {"local_var": int}
        parser = ForwardRefParser(localns=localns)
        assert parser.localns == localns


class TestForwardRefParserEvaluateString:
    """Test cases for _evaluate_string method."""

    def test_evaluate_string_int(self) -> None:
        """Test evaluating 'int' string."""
        parser = ForwardRefParser()
        result = parser._evaluate_string("int")
        assert result is int

    def test_evaluate_string_list_int(self) -> None:
        """Test evaluating 'list[int]' string."""
        parser = ForwardRefParser()
        result = parser._evaluate_string("list[int]")
        assert result == list[int]

    def test_evaluate_string_optional(self) -> None:
        """Test evaluating 'Optional[str]' string."""
        parser = ForwardRefParser()
        result = parser._evaluate_string("Optional[str]")
        assert result == Optional[str]

    def test_evaluate_string_undefined_raises(self) -> None:
        """Test evaluating undefined type raises NameError."""
        parser = ForwardRefParser()
        with pytest.raises(NameError):
            parser._evaluate_string("UndefinedType")


@pytest.mark.parametrize(
    ("forward_ref_string", "expected"),
    [
        ("int", nw.Int64()),
        ("str", nw.String()),
        ("float", nw.Float64()),
        ("bool", nw.Boolean()),
        ("list[int]", nw.List(nw.Int64())),
        ("list[str]", nw.List(nw.String())),
        ("tuple[int, ...]", nw.List(nw.Int64())),
        ("List[int]", nw.List(nw.Int64())),
    ],
)
def test_parse_forward_ref_parametrized(forward_ref_string: str, expected: nw.DType) -> None:
    """Parametrized test for ForwardRef parsing."""
    forward_ref_parser = ForwardRefParser()
    py_parser = PyTypeParser()
    chain = ParserChain([forward_ref_parser, py_parser])
    forward_ref_parser.parser_chain = chain
    py_parser.parser_chain = chain

    result = forward_ref_parser.parse(ForwardRef(forward_ref_string))
    assert result == expected
