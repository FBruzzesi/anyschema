from __future__ import annotations

import sys
from dataclasses import dataclass, field, make_dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

import pytest
from pydantic.dataclasses import dataclass as pydantic_dataclass

from anyschema.adapters import dataclass_adapter
from tests.conftest import DataclassEventWithTimeMetadata

if TYPE_CHECKING:
    from anyschema.typing import DataclassType


class PersonIntoDataclass:
    name: str
    age: int
    date_of_birth: date


@pytest.mark.parametrize(
    "spec",
    [
        pydantic_dataclass(PersonIntoDataclass),
        dataclass(PersonIntoDataclass),
        make_dataclass("Test", [("name", str), ("age", int), ("date_of_birth", date)]),
    ],
)
def test_dataclass_adapter(spec: DataclassType) -> None:
    expected = (("name", str, (), {}), ("age", int, (), {}), ("date_of_birth", date, (), {}))
    result = tuple(dataclass_adapter(spec))
    assert result == expected


def test_dataclass_adapter_missing_decorator_raises() -> None:
    """Test that adapter raises helpful error when child class isn't decorated."""

    @dataclass
    class Base:
        foo: str

    class ChildWithoutDecorator(Base):
        bar: int

    expected_msg = (
        "Class 'ChildWithoutDecorator' has annotations ('bar') that are not dataclass fields. "
        "If this class inherits from a dataclass, you must also decorate it with @dataclass "
        "to properly define these fields."
    )

    with pytest.raises(AssertionError, match=expected_msg.replace("(", r"\(").replace(")", r"\)")):
        list(dataclass_adapter(ChildWithoutDecorator))  # type: ignore[arg-type]


def test_dataclass_adapter_with_time_metadata() -> None:
    result = list(dataclass_adapter(DataclassEventWithTimeMetadata))

    expected = [
        ("name", str, (), {"__anyschema_metadata__": {"description": "Event name"}}),
        ("created_at", datetime, (), {}),
        (
            "scheduled_at",
            datetime,
            (),
            {"__anyschema_metadata__": {"time_zone": "UTC", "description": "Scheduled time"}},
        ),
        ("started_at", datetime, (), {"__anyschema_metadata__": {"time_unit": "ms"}}),
        ("completed_at", datetime, (), {"__anyschema_metadata__": {"time_zone": "Europe/Berlin", "time_unit": "ns"}}),
    ]

    assert result == expected


@pytest.mark.skipif(sys.version_info < (3, 14), reason="doc parameter requires Python 3.14+")
def test_dataclass_adapter_with_doc_argument() -> None:
    @dataclass
    class Product:
        name: str = field(doc="Product name")  # type: ignore[call-arg]
        price: float = field(doc="Product price")  # type: ignore[call-arg]
        in_stock: bool

    result = list(dataclass_adapter(Product))

    expected = [
        ("name", str, (), {"__anyschema_metadata__": {"description": "Product name"}}),
        ("price", float, (), {"__anyschema_metadata__": {"description": "Product price"}}),
        ("in_stock", bool, (), {}),
    ]

    assert result == expected


@pytest.mark.skipif(sys.version_info < (3, 14), reason="doc parameter requires Python 3.14+")
def test_dataclass_adapter_doc_metadata_precedence() -> None:
    @dataclass
    class Product:
        # metadata description should take precedence
        name: str = field(  # type: ignore[call-arg]
            doc="From doc argument", metadata={"__anyschema_metadata__": {"description": "From metadata"}}
        )

    result = list(dataclass_adapter(Product))

    expected = [
        ("name", str, (), {"__anyschema_metadata__": {"description": "From metadata"}}),
    ]

    assert result == expected
