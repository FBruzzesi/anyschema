from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated

import pytest
from annotated_types import Ge
from pydantic import BaseModel, Field

from anyschema.adapters import pydantic_adapter
from tests.conftest import PydanticEventWithTimeMetadata

if TYPE_CHECKING:
    from anyschema.typing import FieldSpec


class SimpleModel(BaseModel):
    name: str
    age: int


class ModelWithConstraints(BaseModel):
    name: str
    age: Annotated[int, Field(ge=0)]


class ModelWithDescriptions(BaseModel):
    id: int = Field(description="ID")
    name: str = Field(description="Product name", json_schema_extra={"format": "name"})
    tags: list[str] = Field(description="tags", json_schema_extra={"anyschema/description": "Override"})


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (SimpleModel, (("name", str, (), {}), ("age", int, (), {}))),
        (ModelWithConstraints, (("name", str, (), {}), ("age", int, (Ge(ge=0),), {}))),
        (
            ModelWithDescriptions,
            (
                ("id", int, (), {"anyschema/description": "ID"}),
                ("name", str, (), {"anyschema/description": "Product name", "format": "name"}),
                ("tags", list[str], (), {"anyschema/description": "Override"}),
            ),
        ),
    ],
)
def test_pydantic_adapter(spec: type[BaseModel], expected: tuple[FieldSpec, ...]) -> None:
    result = tuple(pydantic_adapter(spec))
    assert result == expected


def test_pydantic_adapter_with_json_schema_extra() -> None:
    result = list(pydantic_adapter(PydanticEventWithTimeMetadata))

    expected = [
        ("name", str, (), {}),
        ("created_at", datetime, (), {}),
        ("scheduled_at", datetime, (), {"anyschema/time_zone": "UTC"}),
        ("started_at", datetime, (), {"anyschema/time_unit": "ms"}),
        ("completed_at", datetime, (), {"anyschema/time_zone": "Europe/Berlin", "anyschema/time_unit": "ns"}),
    ]

    assert result == expected
