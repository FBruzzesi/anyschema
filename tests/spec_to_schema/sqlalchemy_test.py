from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

import narwhals as nw
import pytest

from anyschema import AnySchema
from tests.conftest import (
    ComplexORM,
    EventORMWithTimeMetadata,
    ProductORM,
    SimpleUserORM,
    array_fixed_table,
    array_list_table,
    bigint_table,
    complex_table,
    event_table_with_time_metadata,
    event_table_with_tz_aware,
    user_table,
)

if TYPE_CHECKING:
    from anyschema.typing import SQLAlchemyTableType


@pytest.mark.parametrize(
    ("spec", "expected_schema"),
    [
        # ORM models
        (
            SimpleUserORM,
            {
                "id": nw.Int32(),
                "name": nw.String(),
            },
        ),
        (
            ProductORM,
            {
                "id": nw.Int32(),
                "name": nw.String(),
                "price": nw.Float32(),
                "in_stock": nw.Boolean(),
            },
        ),
        (
            ComplexORM,
            {
                "id": nw.Int32(),
                "name": nw.String(),
                "description": nw.String(),
                "age": nw.Int32(),
                "score": nw.Float32(),
                "is_active": nw.Boolean(),
                "created_at": nw.Datetime(),
                "birth_date": nw.Date(),
            },
        ),
        # Core tables
        (
            user_table,
            {
                "id": nw.Int32(),
                "name": nw.String(),
                "age": nw.Int32(),
                "email": nw.String(),
            },
        ),
        (
            complex_table,
            {
                "id": nw.Int32(),
                "name": nw.String(),
                "description": nw.String(),
                "age": nw.Int32(),
                "score": nw.Float32(),
                "is_active": nw.Boolean(),
                "created_at": nw.Datetime(),
                "birth_date": nw.Date(),
            },
        ),
        (
            bigint_table,
            {
                "id": nw.Int64(),
                "count": nw.Int64(),
            },
        ),
        # Array types - List (no dimensions)
        (
            array_list_table,
            {
                "id": nw.Int32(),
                "tags": nw.List(nw.String()),
                "scores": nw.List(nw.Float32()),
            },
        ),
        # Array types - Fixed dimensions (Array)
        (
            array_fixed_table,
            {
                "id": nw.Int32(),
                "coordinates": nw.Array(nw.Float32(), shape=(3,)),
                "matrix": nw.Array(nw.Int32(), shape=(2,)),
            },
        ),
    ],
)
def test_sqlalchemy_spec(spec: SQLAlchemyTableType, expected_schema: Mapping[str, nw.dtypes.DType]) -> None:
    schema = AnySchema(spec=spec)
    nw_schema = schema._nw_schema
    assert nw_schema == nw.Schema(expected_schema)


@pytest.mark.parametrize(
    ("spec", "expected_schema"),
    [
        # Table with time metadata
        (
            event_table_with_time_metadata,
            {
                "id": nw.Int32(),
                "name": nw.String(),
                "created_at": nw.Datetime(),
                "scheduled_at": nw.Datetime(time_zone="UTC"),
                "started_at": nw.Datetime(time_unit="ms"),
                "completed_at": nw.Datetime(time_unit="ns", time_zone="Europe/Berlin"),
            },
        ),
        # ORM with time metadata
        (
            EventORMWithTimeMetadata,
            {
                "id": nw.Int32(),
                "name": nw.String(),
                "created_at": nw.Datetime(),
                "scheduled_at": nw.Datetime(time_zone="UTC"),
                "started_at": nw.Datetime(time_unit="ms"),
                "completed_at": nw.Datetime(time_unit="ns", time_zone="Europe/Berlin"),
            },
        ),
        # Table with timezone-aware datetime
        (
            event_table_with_tz_aware,
            {
                "id": nw.Int32(),
                "timestamp_utc": nw.Datetime(time_zone="UTC"),
                "timestamp_berlin": nw.Datetime(time_unit="ms", time_zone="Europe/Berlin"),
            },
        ),
    ],
)
def test_sqlalchemy_spec_with_time_metadata(
    spec: SQLAlchemyTableType, expected_schema: Mapping[str, nw.dtypes.DType]
) -> None:
    """Test that SQLAlchemy specs with time metadata are correctly converted to narwhals schema."""
    schema = AnySchema(spec=spec)
    nw_schema = schema._nw_schema
    assert nw_schema == nw.Schema(expected_schema)
