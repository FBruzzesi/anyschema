from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import attrs
import pytest

from anyschema.adapters import attrs_adapter

if TYPE_CHECKING:
    from anyschema.typing import AttrsClassType


@attrs.define
class PersonAttrs:
    name: str
    age: int
    date_of_birth: date


@attrs.frozen
class PersonAttrsFrozen:
    name: str
    age: int
    date_of_birth: date


@attrs.define
class BookWithMetadata:
    title: str = attrs.field(metadata={"description": "Book title"})
    author: str = attrs.field(metadata={"max_length": 100})


@pytest.mark.parametrize(
    "spec",
    [
        PersonAttrs,
        PersonAttrsFrozen,
    ],
)
def test_attrs_adapter(spec: AttrsClassType) -> None:
    expected = (("name", str, ()), ("age", int, ()), ("date_of_birth", date, ()))
    result = tuple(attrs_adapter(spec))
    assert result == expected


def test_attrs_adapter_with_metadata() -> None:
    """Test that attrs adapter correctly extracts field metadata."""
    result = list(attrs_adapter(BookWithMetadata))
    assert result == [("title", str, ("Book title",)), ("author", str, (100,))]


def test_attrs_adapter_with_inheritance() -> None:
    """Test that attrs adapter correctly handles inheritance."""

    @attrs.define
    class Base:
        foo: str
        bar: int

    @attrs.define
    class Derived(Base):
        baz: float

    result = list(attrs_adapter(Derived))
    # Should include all fields: foo, bar from Base and baz from Derived
    assert result == [("foo", str, ()), ("bar", int, ()), ("baz", float, ())]


def test_attrs_adapter_missing_decorator_raises() -> None:
    """Test that adapter raises helpful error when child class isn't decorated."""

    @attrs.define
    class Base:
        foo: str

    class ChildWithoutDecorator(Base):
        bar: int

    expected_msg = (
        "Class 'ChildWithoutDecorator' has annotations ('bar') that are not attrs fields. "
        "If this class inherits from an attrs class, you must also decorate it with @attrs.define "
        "or @attrs.frozen to properly define these fields."
    )

    with pytest.raises(AssertionError, match=expected_msg.replace("(", r"\(").replace(")", r"\)")):
        list(attrs_adapter(ChildWithoutDecorator))
