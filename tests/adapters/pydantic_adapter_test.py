from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated

import pytest
from annotated_types import Ge
from pydantic import BaseModel, Field

from anyschema.adapters import pydantic_adapter
from tests.conftest import PydanticEventWithTimeMetadata

if TYPE_CHECKING:
    from anyschema.typing import FieldMetadata, FieldSpec

EMPTY_METADATA: FieldMetadata = {}  # Type hinted empty metadata dict


class SimpleModel(BaseModel):
    name: str
    age: int


class ModelWithConstraints(BaseModel):
    name: str
    age: Annotated[int, Field(ge=0)]


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (SimpleModel, (("name", str, (), EMPTY_METADATA), ("age", int, (), EMPTY_METADATA))),
        (ModelWithConstraints, (("name", str, (), EMPTY_METADATA), ("age", int, (Ge(ge=0),), EMPTY_METADATA))),
    ],
)
def test_pydantic_adapter(spec: type[BaseModel], expected: tuple[FieldSpec, ...]) -> None:
    result = tuple(pydantic_adapter(spec))
    assert result == expected


def test_pydantic_adapter_with_json_schema_extra() -> None:
    result = tuple(pydantic_adapter(PydanticEventWithTimeMetadata))

    expected: tuple[FieldSpec, ...] = (
        ("name", str, (), EMPTY_METADATA),
        ("created_at", datetime, (), EMPTY_METADATA),
        ("scheduled_at", datetime, (), {"anyschema/time_zone": "UTC"}),
        ("started_at", datetime, (), {"anyschema/time_unit": "ms"}),
        ("completed_at", datetime, (), {"anyschema/time_zone": "Europe/Berlin", "anyschema/time_unit": "ns"}),
    )

    assert result == expected
