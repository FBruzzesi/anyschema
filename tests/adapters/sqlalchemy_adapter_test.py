from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import BigInteger, Float, Integer, String
from sqlalchemy.types import TypeEngine

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
                ("id", Integer(), (), {}),
                ("name", String(), (), {"anyschema/nullable": True}),
            ],
        ),
        (
            UserWithTypesORM,
            [
                ("id", Integer(), (), {}),
                ("name", String(50), (), {}),
                ("age", Integer(), (), {"anyschema/nullable": True}),
                ("score", Float(), (), {"anyschema/nullable": True}),
            ],
        ),
        (
            user_table,
            [
                (
                    "id",
                    Integer(),
                    (),
                    {"anyschema/description": "Primary key"},
                ),
                ("name", String(50), (), {"anyschema/nullable": True}),
                (
                    "age",
                    Integer(),
                    (),
                    {"anyschema/description": "User age", "anyschema/nullable": True},
                ),
                ("email", String(100), (), {"anyschema/nullable": True}),
            ],
        ),
        (
            numeric_table,
            [
                ("int_col", Integer(), (), {"anyschema/nullable": True}),
                ("bigint_col", BigInteger(), (), {"anyschema/nullable": True}),
                ("string_col", String(100), (), {"anyschema/nullable": True}),
                ("float_col", Float(), (), {"anyschema/nullable": True}),
            ],
        ),
    ],
)
def test_sqlalchemy_adapter(spec: SQLAlchemyTableType, expected: list[FieldSpec]) -> None:
    result = sqlalchemy_adapter(spec)
    assert_result_equal(result, expected)


def test_sqlalchemy_adapter_invalid_type() -> None:
    msg = "Expected SQLAlchemy Table or DeclarativeBase subclass, got 'str'"
    with pytest.raises(TypeError, match=msg):
        list(sqlalchemy_adapter("not a table"))  # type: ignore[arg-type]


def test_sqlalchemy_adapter_with_time_metadata_table() -> None:
    """Test that SQLAlchemy Table adapter correctly extracts time metadata from column.info."""
    from sqlalchemy.types import DateTime

    result = list(sqlalchemy_adapter(event_table_with_time_metadata))

    expected = [
        ("id", Integer(), (), {}),
        ("name", String(100), (), {"anyschema/nullable": True}),
        ("created_at", DateTime(), (), {"anyschema/nullable": True}),
        ("scheduled_at", DateTime(timezone=True), (), {"anyschema/nullable": True, "anyschema/time_zone": "UTC"}),
        ("started_at", DateTime(), (), {"anyschema/nullable": True, "anyschema/time_unit": "ms"}),
        (
            "completed_at",
            DateTime(timezone=True),
            (),
            {"anyschema/nullable": True, "anyschema/time_zone": "Europe/Berlin", "anyschema/time_unit": "ns"},
        ),
    ]

    assert_result_equal(result, expected)


def test_sqlalchemy_adapter_with_time_metadata_orm() -> None:
    """Test that SQLAlchemy ORM adapter correctly extracts time metadata from mapped_column info."""
    from sqlalchemy.types import DateTime

    result = list(sqlalchemy_adapter(EventORMWithTimeMetadata))

    expected = [
        ("id", Integer(), (), {}),
        ("name", String(), (), {}),
        ("created_at", DateTime(), (), {}),
        ("scheduled_at", DateTime(timezone=True), (), {"anyschema/time_zone": "UTC"}),
        ("started_at", DateTime(), (), {"anyschema/time_unit": "ms"}),
        (
            "completed_at",
            DateTime(timezone=True),
            (),
            {"anyschema/time_zone": "Europe/Berlin", "anyschema/time_unit": "ns"},
        ),
    ]

    assert_result_equal(result, expected)


def test_sqlalchemy_adapter_with_tz_aware_datetime() -> None:
    """Test that SQLAlchemy adapter correctly extracts timezone-aware datetime metadata."""
    from sqlalchemy.types import DateTime as SQLADateTime

    result = list(sqlalchemy_adapter(event_table_with_tz_aware))

    expected = [
        ("id", Integer(), (), {}),
        ("timestamp_utc", SQLADateTime(timezone=True), (), {"anyschema/nullable": True, "anyschema/time_zone": "UTC"}),
        (
            "timestamp_berlin",
            SQLADateTime(timezone=True),
            (),
            {"anyschema/nullable": True, "anyschema/time_zone": "Europe/Berlin", "anyschema/time_unit": "ms"},
        ),
    ]

    assert_result_equal(result, expected)
