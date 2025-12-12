from __future__ import annotations

import attrs
import narwhals as nw
import pytest

from anyschema.parsers import ParserPipeline, PyTypeStep
from anyschema.parsers.attrs import AttrsTypeStep
from tests.conftest import AttrsDerived, AttrsPerson, AttrsPersonFrozen, create_missing_decorator_test_case


@pytest.fixture(scope="module")
def attrs_parser() -> AttrsTypeStep:
    attrs_parser = AttrsTypeStep()
    py_parser = PyTypeStep()
    chain = ParserPipeline([attrs_parser, py_parser])
    attrs_parser.pipeline = chain
    py_parser.pipeline = chain
    return attrs_parser


def test_parse_attrs_class_into_struct(attrs_parser: AttrsTypeStep) -> None:
    result = attrs_parser.parse(AttrsPerson, (), {})

    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="age", dtype=nw.Int64()),
        nw.Field(name="date_of_birth", dtype=nw.Date()),
        nw.Field(name="is_active", dtype=nw.Boolean()),
        nw.Field(name="classes", dtype=nw.List(nw.String())),
        nw.Field(name="grades", dtype=nw.List(nw.Float64())),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_frozen_attrs_class(attrs_parser: AttrsTypeStep) -> None:
    result = attrs_parser.parse(AttrsPersonFrozen, (), {})

    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="age", dtype=nw.Int64()),
        nw.Field(name="date_of_birth", dtype=nw.Date()),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_empty_attrs_class(attrs_parser: AttrsTypeStep) -> None:
    @attrs.define
    class EmptyClass:
        pass

    result = attrs_parser.parse(EmptyClass, (), {})
    expected = nw.Struct([])
    assert result == expected


def test_parse_non_attrs_class_returns_none(attrs_parser: AttrsTypeStep) -> None:
    class RegularClass:
        pass

    result = attrs_parser.parse(RegularClass, (), {})
    assert result is None


def test_parse_classic_attr_s_decorator(attrs_parser: AttrsTypeStep) -> None:
    import attr

    @attr.s(auto_attribs=True)
    class ClassicAttrs:
        name: str
        value: int

    result = attrs_parser.parse(ClassicAttrs, (), {})

    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="value", dtype=nw.Int64()),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_attrs_with_inheritance(attrs_parser: AttrsTypeStep) -> None:
    result = attrs_parser.parse(AttrsDerived, (), {})

    expected_fields = [
        nw.Field(name="foo", dtype=nw.String()),
        nw.Field(name="bar", dtype=nw.Int64()),
        nw.Field(name="baz", dtype=nw.Float64()),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_attrs_missing_decorator_raises(attrs_parser: AttrsTypeStep) -> None:
    child_cls, expected_msg = create_missing_decorator_test_case()
    with pytest.raises(AssertionError, match=expected_msg.replace("(", r"\(").replace(")", r"\)")):
        attrs_parser.parse(child_cls, (), {})
