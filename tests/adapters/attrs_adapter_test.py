from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import attrs
import pytest

from anyschema.adapters import attrs_adapter
from tests.conftest import AttrsDerived, create_missing_decorator_test_case

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
    result = list(attrs_adapter(AttrsDerived))
    # Should include all fields: foo, bar from Base and baz from Derived
    assert result == [("foo", str, ()), ("bar", int, ()), ("baz", float, ())]


def test_attrs_adapter_missing_decorator_raises() -> None:
    """Test that adapter raises helpful error when child class isn't decorated."""
    child_cls, expected_msg = create_missing_decorator_test_case()
    with pytest.raises(AssertionError, match=expected_msg.replace("(", r"\(").replace(")", r"\)")):
        list(attrs_adapter(child_cls))
