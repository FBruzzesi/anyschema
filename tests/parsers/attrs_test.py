from __future__ import annotations

import attrs
import narwhals as nw
import pytest

from anyschema.parsers import ParserPipeline, PyTypeStep
from anyschema.parsers.attrs import AttrsTypeStep
from tests.conftest import AttrsDerived, AttrsPerson, create_missing_decorator_test_case


@pytest.fixture(scope="module")
def attrs_parser() -> AttrsTypeStep:
    """Create an AttrsTypeStep instance with pipeline set."""
    attrs_parser = AttrsTypeStep()
    py_parser = PyTypeStep()
    chain = ParserPipeline([attrs_parser, py_parser])
    attrs_parser.pipeline = chain
    py_parser.pipeline = chain
    return attrs_parser


def test_parse_attrs_class_into_struct(attrs_parser: AttrsTypeStep) -> None:
    @attrs.define
    class SomeAttrsClass:
        name: str
        age: int
        active: bool

    result = attrs_parser.parse(SomeAttrsClass)

    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="age", dtype=nw.Int64()),
        nw.Field(name="active", dtype=nw.Boolean()),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_frozen_attrs_class(attrs_parser: AttrsTypeStep) -> None:
    @attrs.frozen
    class FrozenClass:
        x: int
        y: float

    result = attrs_parser.parse(FrozenClass)

    expected_fields = [
        nw.Field(name="x", dtype=nw.Int64()),
        nw.Field(name="y", dtype=nw.Float64()),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_nested_attrs_classes(attrs_parser: AttrsTypeStep) -> None:
    result = attrs_parser.parse(AttrsPerson)

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


def test_parse_empty_attrs_class(attrs_parser: AttrsTypeStep) -> None:
    """Test parsing an empty attrs class."""

    @attrs.define
    class EmptyClass:
        pass

    result = attrs_parser.parse(EmptyClass)

    expected = nw.Struct([])
    assert result == expected


def test_parse_attrs_with_lists(attrs_parser: AttrsTypeStep) -> None:
    """Test parsing attrs class with list fields."""

    @attrs.define
    class ClassWithLists:
        names: list[str]
        scores: list[int]

    result = attrs_parser.parse(ClassWithLists)

    expected_fields = [
        nw.Field(name="names", dtype=nw.List(nw.String())),
        nw.Field(name="scores", dtype=nw.List(nw.Int64())),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_non_attrs_class_returns_none(attrs_parser: AttrsTypeStep) -> None:
    """Test that parser returns None for non-attrs classes."""

    class RegularClass:
        pass

    result = attrs_parser.parse(RegularClass)
    assert result is None


def test_parse_classic_attr_s_decorator(attrs_parser: AttrsTypeStep) -> None:
    """Test parsing attrs class using classic @attr.s decorator."""
    import attr

    @attr.s(auto_attribs=True)
    class ClassicAttrs:
        name: str
        value: int

    result = attrs_parser.parse(ClassicAttrs)

    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="value", dtype=nw.Int64()),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_attrs_with_inheritance(attrs_parser: AttrsTypeStep) -> None:
    """Test parsing attrs class with inheritance."""
    result = attrs_parser.parse(AttrsDerived)

    expected_fields = [
        nw.Field(name="foo", dtype=nw.String()),
        nw.Field(name="bar", dtype=nw.Int64()),
        nw.Field(name="baz", dtype=nw.Float64()),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_attrs_missing_decorator_raises(attrs_parser: AttrsTypeStep) -> None:
    """Test that parser raises helpful error when child class isn't decorated."""
    child_cls, expected_msg = create_missing_decorator_test_case()
    with pytest.raises(AssertionError, match=expected_msg.replace("(", r"\(").replace(")", r"\)")):
        attrs_parser.parse(child_cls)
