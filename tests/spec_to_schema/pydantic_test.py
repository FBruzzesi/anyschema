from __future__ import annotations

from typing import Any, Mapping

import narwhals as nw
import pytest
from pydantic import BaseModel

from anyschema import AnySchema
from tests.conftest import (
    PydanticEventWithTimeMetadata,
    PydanticSpecialDatetimeWithMetadata,
    PydanticStudent,
)


class PydanticLooseRecord(BaseModel):
    a: Any
    b: list[Any]
    c: dict[str, int]
    d: dict[str, Any]


# Typed explicitly so mypy uses this element type instead of joining the model constructors
# (which would otherwise produce a spurious `list-item` error on the later cases).
PYDANTIC_MODEL_CASES: list[tuple[type[BaseModel], Mapping[str, nw.dtypes.DType]]] = [
    (
        PydanticStudent,
        {
            "name": nw.String(),
            "date_of_birth": nw.Date(),
            "age": nw.UInt64(),
            "classes": nw.List(nw.String()),
            "has_graduated": nw.Boolean(),
        },
    ),
    (
        PydanticEventWithTimeMetadata,
        {
            "name": nw.String(),
            "created_at": nw.Datetime("us"),
            "scheduled_at": nw.Datetime("us", time_zone="UTC"),
            "started_at": nw.Datetime("ms"),
            "completed_at": nw.Datetime("ns", time_zone="Europe/Berlin"),
        },
    ),
    (
        PydanticSpecialDatetimeWithMetadata,
        {
            "aware": nw.Datetime("us", time_zone="UTC"),
            "aware_ms": nw.Datetime("ms", time_zone="Asia/Tokyo"),
            "naive_ms": nw.Datetime("ms"),
            "past_utc": nw.Datetime("us", time_zone="UTC"),
            "future_ns": nw.Datetime("ns"),
        },
    ),
    (
        PydanticLooseRecord,
        {
            "a": nw.Object(),
            "b": nw.List(nw.Object()),
            "c": nw.Map(nw.String(), nw.Int64()),
            "d": nw.Map(nw.String(), nw.Object()),
        },
    ),
]


@pytest.mark.parametrize(("spec", "expected_schema"), PYDANTIC_MODEL_CASES)
def test_pydantic_model(spec: type[BaseModel], expected_schema: Mapping[str, nw.dtypes.DType]) -> None:
    schema = AnySchema(spec=spec)
    nw_schema = schema._nw_schema
    assert nw_schema == nw.Schema(expected_schema)
