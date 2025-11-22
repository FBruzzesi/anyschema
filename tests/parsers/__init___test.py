from __future__ import annotations

from typing import Annotated, Optional

import narwhals as nw
import pytest
from annotated_types import Gt
from pydantic import BaseModel, PositiveInt

from anyschema.parsers import (
    AnnotatedParser,
    ForwardRefParser,
    ParserChain,
    PyTypeParser,
    UnionTypeParser,
    create_parser_chain,
)
from anyschema.parsers.annotated_types import AnnotatedTypesParser
from anyschema.parsers.pydantic import PydanticTypeParser


class TestCreateParserChainAuto:
    """Test cases for create_parser_chain with auto mode."""

    def test_create_parser_chain_auto_pydantic(self) -> None:
        """Test creating parser chain with auto mode for pydantic."""
        chain = create_parser_chain("auto", spec_type="pydantic")

        assert isinstance(chain, ParserChain)
        assert len(chain.parsers) == 6

        # Verify order: ForwardRef, Union, Annotated, AnnotatedTypes, Pydantic, Python
        assert isinstance(chain.parsers[0], ForwardRefParser)
        assert isinstance(chain.parsers[1], UnionTypeParser)
        assert isinstance(chain.parsers[2], AnnotatedParser)
        assert isinstance(chain.parsers[3], AnnotatedTypesParser)
        assert isinstance(chain.parsers[4], PydanticTypeParser)
        assert isinstance(chain.parsers[5], PyTypeParser)

    def test_create_parser_chain_auto_python(self) -> None:
        """Test creating parser chain with auto mode for python."""
        chain = create_parser_chain("auto", spec_type="python")

        assert isinstance(chain, ParserChain)
        assert len(chain.parsers) == 5

        # Verify order: ForwardRef, Union, Annotated, AnnotatedTypes, Python
        assert isinstance(chain.parsers[0], ForwardRefParser)
        assert isinstance(chain.parsers[1], UnionTypeParser)
        assert isinstance(chain.parsers[2], AnnotatedParser)
        assert isinstance(chain.parsers[3], AnnotatedTypesParser)
        assert isinstance(chain.parsers[4], PyTypeParser)

    def test_create_parser_chain_auto_none_spec_type(self) -> None:
        """Test creating parser chain with auto mode and None spec_type."""
        chain = create_parser_chain("auto", spec_type=None)

        assert isinstance(chain, ParserChain)
        assert len(chain.parsers) == 5

        # Should default to python-like behavior without pydantic parser
        assert isinstance(chain.parsers[0], ForwardRefParser)
        assert isinstance(chain.parsers[1], UnionTypeParser)
        assert isinstance(chain.parsers[2], AnnotatedParser)
        assert isinstance(chain.parsers[3], AnnotatedTypesParser)
        assert isinstance(chain.parsers[4], PyTypeParser)

    def test_create_parser_chain_default_auto(self) -> None:
        """Test that parsers defaults to 'auto'."""
        chain = create_parser_chain()

        assert isinstance(chain, ParserChain)
        # Should create with default python-like parsers
        assert len(chain.parsers) == 5


class TestCreateParserChainCustom:
    """Test cases for create_parser_chain with custom parsers."""

    def test_create_parser_chain_custom_single(self) -> None:
        """Test creating parser chain with single custom parser."""
        py_parser = PyTypeParser()
        chain = create_parser_chain(parsers=(py_parser,))

        assert isinstance(chain, ParserChain)
        assert len(chain.parsers) == 1
        assert chain.parsers[0] is py_parser

    def test_create_parser_chain_custom_multiple(self) -> None:
        """Test creating parser chain with multiple custom parsers."""
        py_parser = PyTypeParser()
        union_parser = UnionTypeParser()
        chain = create_parser_chain(parsers=(union_parser, py_parser))

        assert isinstance(chain, ParserChain)
        assert len(chain.parsers) == 2
        assert chain.parsers[0] is union_parser
        assert chain.parsers[1] is py_parser

    def test_create_parser_chain_custom_order(self) -> None:
        """Test that custom parser order is preserved."""
        parser1 = PyTypeParser()
        parser2 = UnionTypeParser()
        parser3 = AnnotatedParser()
        chain = create_parser_chain(parsers=(parser1, parser2, parser3))

        assert chain.parsers[0] is parser1
        assert chain.parsers[1] is parser2
        assert chain.parsers[2] is parser3


class TestCreateParserChainWiresReferences:
    """Test that parser_chain references are wired correctly."""

    def test_auto_chain_wires_references(self) -> None:
        """Test that auto chain wires parser_chain references."""
        chain = create_parser_chain("auto", spec_type="python")

        # All parsers should have parser_chain set
        for parser in chain.parsers:
            assert parser.parser_chain is chain

    def test_custom_chain_wires_references(self) -> None:
        """Test that custom chain wires parser_chain references."""
        py_parser = PyTypeParser()
        union_parser = UnionTypeParser()
        chain = create_parser_chain(parsers=(union_parser, py_parser))

        # All parsers should have parser_chain set
        assert py_parser.parser_chain is chain
        assert union_parser.parser_chain is chain


class TestCreateParserChainCaching:
    """Test that create_parser_chain caching works correctly."""

    def test_create_parser_chain_cached_same_params(self) -> None:
        """Test that same parameters return cached result."""
        chain1 = create_parser_chain("auto", spec_type="pydantic")
        chain2 = create_parser_chain("auto", spec_type="pydantic")

        # Due to lru_cache, should be the same object
        assert chain1 is chain2

    def test_create_parser_chain_cached_different_params(self) -> None:
        """Test that different parameters create different chains."""
        chain1 = create_parser_chain("auto", spec_type="pydantic")
        chain2 = create_parser_chain("auto", spec_type="python")

        # Different parameters should create different chains
        assert chain1 is not chain2
        assert len(chain1.parsers) != len(chain2.parsers)

    def test_create_parser_chain_custom_not_cached(self) -> None:
        """Test that custom parsers with tuple are hashable and can be cached."""
        # Custom parser tuples are hashable and can be cached
        py_parser = PyTypeParser()
        chain1 = create_parser_chain(parsers=(py_parser,))
        chain2 = create_parser_chain(parsers=(py_parser,))

        # Due to caching, same parser tuple should return same chain
        assert chain1 is chain2
        assert isinstance(chain1, ParserChain)


class TestParserChainIntegrationBasic:
    """Integration tests for parser chain with basic types."""

    def test_pydantic_chain_parses_int(self) -> None:
        """Test pydantic chain parses int correctly."""
        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(int)
        assert result == nw.Int64()

    def test_pydantic_chain_parses_str(self) -> None:
        """Test pydantic chain parses str correctly."""
        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(str)
        assert result == nw.String()

    def test_python_chain_parses_int(self) -> None:
        """Test python chain parses int correctly."""
        chain = create_parser_chain("auto", spec_type="python")
        result = chain.parse(int)
        assert result == nw.Int64()

    def test_python_chain_parses_list(self) -> None:
        """Test python chain parses list correctly."""
        chain = create_parser_chain("auto", spec_type="python")
        result = chain.parse(list[int])
        assert result == nw.List(nw.Int64())


class TestParserChainIntegrationComplex:
    """Integration tests for parser chain with complex types."""

    def test_pydantic_chain_parses_optional(self) -> None:
        """Test pydantic chain parses Optional correctly."""
        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(Optional[int])
        assert result == nw.Int64()

    def test_pydantic_chain_parses_annotated(self) -> None:
        """Test pydantic chain parses Annotated correctly."""
        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(Annotated[int, "metadata"])
        assert result == nw.Int64()

    def test_pydantic_chain_parses_annotated_with_constraints(self) -> None:
        """Test pydantic chain parses Annotated with constraints."""
        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(Annotated[int, Gt(0)])
        assert result == nw.UInt64()

    def test_pydantic_chain_parses_pydantic_model(self) -> None:
        """Test pydantic chain parses Pydantic models."""

        class SimpleModel(BaseModel):
            name: str
            age: int

        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(SimpleModel)

        expected_fields = [
            nw.Field(name="name", dtype=nw.String()),
            nw.Field(name="age", dtype=nw.Int64()),
        ]
        expected = nw.Struct(expected_fields)
        assert result == expected

    def test_pydantic_chain_parses_positive_int(self) -> None:
        """Test pydantic chain parses PositiveInt correctly."""
        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(PositiveInt)
        assert result == nw.UInt64()

    def test_python_chain_parses_optional(self) -> None:
        """Test python chain parses Optional correctly."""
        chain = create_parser_chain("auto", spec_type="python")
        result = chain.parse(Optional[str])
        assert result == nw.String()

    def test_python_chain_parses_nested_list(self) -> None:
        """Test python chain parses nested list correctly."""
        chain = create_parser_chain("auto", spec_type="python")
        result = chain.parse(list[list[int]])
        assert result == nw.List(nw.List(nw.Int64()))


class TestParserChainIntegrationNested:
    """Integration tests for parser chain with deeply nested types."""

    def test_pydantic_chain_optional_annotated_int(self) -> None:
        """Test parsing Optional[Annotated[int, constraints]]."""
        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(Optional[Annotated[int, Gt(0)]])
        assert result == nw.UInt64()

    def test_pydantic_chain_annotated_optional_int(self) -> None:
        """Test parsing Annotated[Optional[int], metadata]."""
        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(Annotated[Optional[int], "metadata"])
        assert result == nw.Int64()

    def test_pydantic_chain_optional_list(self) -> None:
        """Test parsing Optional[list[int]]."""
        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(Optional[list[int]])
        assert result == nw.List(nw.Int64())

    def test_pydantic_chain_list_optional(self) -> None:
        """Test parsing list[Optional[int]]."""
        chain = create_parser_chain("auto", spec_type="pydantic")
        # list[Optional[int]] is parsed as list[int] - Optional is extracted
        result = chain.parse(list[Optional[int]])
        assert result == nw.List(nw.Int64())


class TestParserChainIntegrationPydanticModels:
    """Integration tests for parser chain with Pydantic models."""

    def test_pydantic_chain_nested_model(self) -> None:
        """Test parsing nested Pydantic models."""

        class Address(BaseModel):
            street: str
            city: str

        class Person(BaseModel):
            name: str
            address: Address

        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(Person)

        address_fields = [
            nw.Field(name="street", dtype=nw.String()),
            nw.Field(name="city", dtype=nw.String()),
        ]
        expected_fields = [
            nw.Field(name="name", dtype=nw.String()),
            nw.Field(name="address", dtype=nw.Struct(address_fields)),
        ]
        expected = nw.Struct(expected_fields)
        assert result == expected

    def test_pydantic_chain_model_with_constraints(self) -> None:
        """Test parsing Pydantic model with constrained fields."""

        class ConstrainedModel(BaseModel):
            age: PositiveInt
            name: str

        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(ConstrainedModel)

        expected_fields = [
            nw.Field(name="age", dtype=nw.UInt64()),
            nw.Field(name="name", dtype=nw.String()),
        ]
        expected = nw.Struct(expected_fields)
        assert result == expected

    def test_pydantic_chain_model_with_list(self) -> None:
        """Test parsing Pydantic model with list fields."""

        class ListModel(BaseModel):
            items: list[str]
            counts: list[int]

        chain = create_parser_chain("auto", spec_type="pydantic")
        result = chain.parse(ListModel)

        expected_fields = [
            nw.Field(name="items", dtype=nw.List(nw.String())),
            nw.Field(name="counts", dtype=nw.List(nw.Int64())),
        ]
        expected = nw.Struct(expected_fields)
        assert result == expected


@pytest.mark.parametrize(
    ("spec_type", "expected_parser_count"),
    [
        ("pydantic", 6),
        ("python", 5),
        (None, 5),
    ],
)
def test_create_parser_chain_auto_parametrized(spec_type: str | None, expected_parser_count: int) -> None:
    """Parametrized test for create_parser_chain auto mode."""
    chain = create_parser_chain("auto", spec_type=spec_type)
    assert len(chain.parsers) == expected_parser_count


@pytest.mark.parametrize(
    ("input_type", "spec_type", "expected"),
    [
        (int, "pydantic", nw.Int64()),
        (str, "pydantic", nw.String()),
        (list[int], "pydantic", nw.List(nw.Int64())),
        (Optional[int], "pydantic", nw.Int64()),
        (int, "python", nw.Int64()),
        (str, "python", nw.String()),
        (list[str], "python", nw.List(nw.String())),
        (Optional[float], "python", nw.Float64()),
    ],
)
def test_parser_chain_parse_parametrized(input_type: type, spec_type: str, expected: nw.DType) -> None:
    """Parametrized test for parser chain parsing."""
    chain = create_parser_chain("auto", spec_type=spec_type)
    result = chain.parse(input_type)
    assert result == expected
