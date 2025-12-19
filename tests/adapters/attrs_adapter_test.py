from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import pytest

from anyschema.adapters import attrs_adapter
from tests.conftest import (
    AttrsBookWithMetadata,
    AttrsDerived,
    AttrsEventWithTimeMetadata,
    AttrsPerson,
    AttrsPersonFrozen,
    create_missing_decorator_test_case,
)

if TYPE_CHECKING:
    from anyschema.typing import AttrsClassType, FieldSpec


@pytest.mark.parametrize(
    "spec",
    [
        AttrsPerson,
        AttrsPersonFrozen,
    ],
)
def test_attrs_adapter(spec: AttrsClassType) -> None:
    result = list(attrs_adapter(spec))
    assert ("name", str, (), {}) in result
    assert ("age", int, (), {}) in result
    assert ("date_of_birth", date, (), {}) in result


def test_attrs_adapter_with_metadata() -> None:
    result = list(attrs_adapter(AttrsBookWithMetadata))
    assert result == [("title", str, (), {"description": "Book title"}), ("author", str, (), {"max_length": 100})]


def test_attrs_adapter_with_inheritance() -> None:
    result = list(attrs_adapter(AttrsDerived))
    assert result == [("foo", str, (), {}), ("bar", int, (), {}), ("baz", float, (), {})]


def test_attrs_adapter_missing_decorator_raises() -> None:
    child_cls, expected_msg = create_missing_decorator_test_case()
    with pytest.raises(AssertionError, match=expected_msg.replace("(", r"\(").replace(")", r"\)")):
        list(attrs_adapter(child_cls))


def test_attrs_adapter_with_time_metadata() -> None:
    result = tuple(attrs_adapter(AttrsEventWithTimeMetadata))
    expected: tuple[FieldSpec, ...] = (
        ("name", str, (), {}),
        ("created_at", datetime, (), {}),
        ("scheduled_at", datetime, (), {"anyschema/time_zone": "UTC"}),
        ("started_at", datetime, (), {"anyschema/time_unit": "ms"}),
        ("completed_at", datetime, (), {"anyschema/time_zone": "Europe/Berlin", "anyschema/time_unit": "ns"}),
    )

    assert result == expected
