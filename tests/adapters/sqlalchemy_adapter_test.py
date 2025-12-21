from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import BigInteger, Float, Integer, String
from sqlalchemy.types import DateTime, TypeEngine

from anyschema.adapters import sqlalchemy_adapter
from tests.conftest import (
    EventORMWithTimeMetadata,
    SimpleUserORM,
    UserWithTypesORM,
    event_table_with_time_metadata,
    event_table_with_tz_aware,
    numeric_table,
    user_table,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from anyschema.typing import FieldSpec, SQLAlchemyTableType


def assert_result_equal(result: Iterable[FieldSpec], expected: Iterable[FieldSpec]) -> None:
    """Helper function that takes care of the fact that sqlalchemy types comparison results in False.

    Namely Integer()==Integer() -> False, therefore we compare their string representation instead.
    """
    for left, right in zip(result, expected, strict=True):
        for lval, rval in zip(left, right, strict=True):
            if isinstance(lval, TypeEngine) and isinstance(rval, TypeEngine):
                assert str(lval) == str(rval), f"{left} != {right}"
            else:
                assert lval == rval, f"{left} != {right}"


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (
            SimpleUserORM,
            [
                ("id", Integer(), (), {"anyschema": {"nullable": False}}),
                ("name", String(), (), {"anyschema": {"nullable": True}}),
            ],
        ),
        (
            UserWithTypesORM,
            [
                ("id", Integer(), (), {"anyschema": {"nullable": False}}),
                ("name", String(50), (), {"anyschema": {"nullable": False}}),
                ("age", Integer(), (), {"anyschema": {"nullable": True}}),
                ("score", Float(), (), {"anyschema": {"nullable": True}}),
            ],
        ),
        (
            user_table,
            [
                (
                    "id",
                    Integer(),
                    (),
                    {"anyschema": {"nullable": False, "description": "Primary key"}},
                ),
                ("name", String(50), (), {"anyschema": {"nullable": True}}),
                (
                    "age",
                    Integer(),
                    (),
                    {"anyschema": {"nullable": True, "description": "User age"}},
                ),
                ("email", String(100), (), {"anyschema": {"nullable": True}}),
            ],
        ),
        (
            numeric_table,
            [
                ("int_col", Integer(), (), {"anyschema": {"nullable": True}}),
                ("bigint_col", BigInteger(), (), {"anyschema": {"nullable": True}}),
                ("string_col", String(100), (), {"anyschema": {"nullable": True}}),
                ("float_col", Float(), (), {"anyschema": {"nullable": True}}),
            ],
        ),
    ],
)
def test_sqlalchemy_adapter(spec: SQLAlchemyTableType, expected: Iterable[FieldSpec]) -> None:
    result = sqlalchemy_adapter(spec)
    assert_result_equal(result, expected)


def test_sqlalchemy_adapter_with_time_metadata_table() -> None:
    """Test that SQLAlchemy Table adapter correctly extracts time metadata from column.info."""
    result = tuple(sqlalchemy_adapter(event_table_with_time_metadata))
    expected: Iterable[FieldSpec] = (
        ("id", Integer(), (), {"anyschema": {"nullable": False}}),
        ("name", String(100), (), {"anyschema": {"nullable": True}}),
        ("created_at", DateTime(), (), {"anyschema": {"nullable": True}}),
        ("scheduled_at", DateTime(timezone=True), (), {"anyschema": {"nullable": True, "time_zone": "UTC"}}),
        ("started_at", DateTime(), (), {"anyschema": {"nullable": True, "time_unit": "ms"}}),
        (
            "completed_at",
            DateTime(timezone=True),
            (),
            {"anyschema": {"nullable": True, "time_zone": "Europe/Berlin", "time_unit": "ns"}},
        ),
    )
    assert_result_equal(result, expected)


def test_sqlalchemy_adapter_with_time_metadata_orm() -> None:
    """Test that SQLAlchemy ORM adapter correctly extracts time metadata from mapped_column info."""
    result = tuple(sqlalchemy_adapter(EventORMWithTimeMetadata))
    expected: Iterable[FieldSpec] = (
        ("id", Integer(), (), {"anyschema": {"nullable": False}}),
        ("name", String(), (), {"anyschema": {"nullable": False}}),
        ("created_at", DateTime(), (), {"anyschema": {"nullable": False}}),
        ("scheduled_at", DateTime(timezone=True), (), {"anyschema": {"nullable": False, "time_zone": "UTC"}}),
        ("started_at", DateTime(), (), {"anyschema": {"nullable": False, "time_unit": "ms"}}),
        (
            "completed_at",
            DateTime(timezone=True),
            (),
            {"anyschema": {"nullable": False, "time_zone": "Europe/Berlin", "time_unit": "ns"}},
        ),
    )
    assert_result_equal(result, expected)


def test_sqlalchemy_adapter_with_tz_aware_datetime() -> None:
    """Test that SQLAlchemy adapter correctly extracts timezone-aware datetime metadata."""
    result = tuple(sqlalchemy_adapter(event_table_with_tz_aware))
    expected: Iterable[FieldSpec] = (
        ("id", Integer(), (), {"anyschema": {"nullable": False}}),
        ("timestamp_utc", DateTime(timezone=True), (), {"anyschema": {"nullable": True, "time_zone": "UTC"}}),
        (
            "timestamp_berlin",
            DateTime(timezone=True),
            (),
            {"anyschema": {"nullable": True, "time_zone": "Europe/Berlin", "time_unit": "ms"}},
        ),
    )
    assert_result_equal(result, expected)
