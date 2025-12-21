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
    from anyschema.typing import DataclassType, FieldSpec


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
    expected: tuple[FieldSpec, ...] = (("name", str, (), {}), ("age", int, (), {}), ("date_of_birth", date, (), {}))
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
        list(dataclass_adapter(ChildWithoutDecorator))


def test_dataclass_adapter_with_time_metadata() -> None:
    result = tuple(dataclass_adapter(DataclassEventWithTimeMetadata))

    expected: tuple[FieldSpec, ...] = (
        ("name", str, (), {"anyschema/description": "Event name"}),
        ("created_at", datetime, (), {}),
        ("scheduled_at", datetime, (), {"anyschema/time_zone": "UTC", "anyschema/description": "Scheduled time"}),
        ("started_at", datetime, (), {"anyschema/time_unit": "ms"}),
        ("completed_at", datetime, (), {"anyschema/time_zone": "Europe/Berlin", "anyschema/time_unit": "ns"}),
    )

    assert result == expected


@pytest.mark.skipif(sys.version_info < (3, 14), reason="doc parameter requires Python 3.14+")
def test_dataclass_adapter_with_doc_argument() -> None:
    @dataclass
    class Product:
        name: str = field(doc="Product name")  # pyright: ignore[reportCallIssue]
        price: float = field(  # pyright: ignore[reportCallIssue]
            doc="Product price",
            metadata={"anyschema/description": "From metadata"},  # anyschema metadata have precedence
        )
        in_stock: bool

    result = list(dataclass_adapter(Product))
    expected = [
        ("name", str, (), {"anyschema/description": "Product name"}),
        ("price", float, (), {"anyschema/description": "From metadata"}),
        ("in_stock", bool, (), {}),
    ]
    assert result == expected
