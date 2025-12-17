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
                (
                    "id",
                    Integer(),
                    (),
                    {"__anyschema_metadata__": {"nullable": False, "unique": False}},
                ),
                (
                    "name",
                    String(),
                    (),
                    {"__anyschema_metadata__": {"nullable": True, "unique": False}},
                ),
            ],
        ),
        (
            UserWithTypesORM,
            [
                (
                    "id",
                    Integer(),
                    (),
                    {"__anyschema_metadata__": {"nullable": False, "unique": False}},
                ),
                (
                    "name",
                    String(50),
                    (),
                    {"__anyschema_metadata__": {"nullable": False, "unique": False}},
                ),
                (
                    "age",
                    Integer(),
                    (),
                    {"__anyschema_metadata__": {"nullable": True, "unique": False}},
                ),
                (
                    "score",
                    Float(),
                    (),
                    {"__anyschema_metadata__": {"nullable": True, "unique": False}},
                ),
            ],
        ),
        (
            user_table,
            [
                (
                    "id",
                    Integer(),
                    (),
                    {"__anyschema_metadata__": {"description": "Primary key", "nullable": False, "unique": False}},
                ),
                (
                    "name",
                    String(50),
                    (),
                    {"__anyschema_metadata__": {"nullable": True, "unique": False}},
                ),
                (
                    "age",
                    Integer(),
                    (),
                    {"__anyschema_metadata__": {"description": "User age", "nullable": True, "unique": False}},
                ),
                (
                    "email",
                    String(100),
                    (),
                    {"__anyschema_metadata__": {"nullable": True, "unique": False}},
                ),
            ],
        ),
        (
            numeric_table,
            [
                (
                    "int_col",
                    Integer(),
                    (),
                    {"__anyschema_metadata__": {"nullable": True, "unique": False}},
                ),
                (
                    "bigint_col",
                    BigInteger(),
                    (),
                    {"__anyschema_metadata__": {"nullable": True, "unique": False}},
                ),
                (
                    "string_col",
                    String(100),
                    (),
                    {"__anyschema_metadata__": {"nullable": True, "unique": False}},
                ),
                (
                    "float_col",
                    Float(),
                    (),
                    {"__anyschema_metadata__": {"nullable": True, "unique": False}},
                ),
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
        (
            "id",
            Integer(),
            (),
            {"__anyschema_metadata__": {"nullable": False, "unique": False}},
        ),
        (
            "name",
            String(100),
            (),
            {"__anyschema_metadata__": {"nullable": True, "unique": False}},
        ),
        (
            "created_at",
            DateTime(),
            (),
            {"__anyschema_metadata__": {"nullable": True, "unique": False}},
        ),
        (
            "scheduled_at",
            DateTime(timezone=True),
            (),
            {
                "__anyschema_metadata__": {
                    "nullable": True,
                    "unique": False,
                    "time_zone": "UTC",
                }
            },
        ),
        (
            "started_at",
            DateTime(),
            (),
            {
                "__anyschema_metadata__": {
                    "nullable": True,
                    "unique": False,
                    "time_unit": "ms",
                }
            },
        ),
        (
            "completed_at",
            DateTime(timezone=True),
            (),
            {
                "__anyschema_metadata__": {
                    "nullable": True,
                    "unique": False,
                    "time_zone": "Europe/Berlin",
                    "time_unit": "ns",
                }
            },
        ),
    ]

    assert_result_equal(result, expected)


def test_sqlalchemy_adapter_with_time_metadata_orm() -> None:
    """Test that SQLAlchemy ORM adapter correctly extracts time metadata from mapped_column info."""
    from sqlalchemy.types import DateTime

    result = list(sqlalchemy_adapter(EventORMWithTimeMetadata))

    expected = [
        (
            "id",
            Integer(),
            (),
            {"__anyschema_metadata__": {"nullable": False, "unique": False}},
        ),
        (
            "name",
            String(),
            (),
            {"__anyschema_metadata__": {"nullable": False, "unique": False}},
        ),
        (
            "created_at",
            DateTime(),
            (),
            {"__anyschema_metadata__": {"nullable": False, "unique": False}},
        ),
        (
            "scheduled_at",
            DateTime(timezone=True),
            (),
            {
                "__anyschema_metadata__": {
                    "nullable": False,
                    "unique": False,
                    "time_zone": "UTC",
                }
            },
        ),
        (
            "started_at",
            DateTime(),
            (),
            {
                "__anyschema_metadata__": {
                    "nullable": False,
                    "unique": False,
                    "time_unit": "ms",
                }
            },
        ),
        (
            "completed_at",
            DateTime(timezone=True),
            (),
            {
                "__anyschema_metadata__": {
                    "nullable": False,
                    "unique": False,
                    "time_zone": "Europe/Berlin",
                    "time_unit": "ns",
                }
            },
        ),
    ]

    assert_result_equal(result, expected)


def test_sqlalchemy_adapter_with_tz_aware_datetime() -> None:
    """Test that SQLAlchemy adapter correctly extracts timezone-aware datetime metadata."""
    from sqlalchemy.types import DateTime as SQLADateTime

    result = list(sqlalchemy_adapter(event_table_with_tz_aware))

    expected = [
        (
            "id",
            Integer(),
            (),
            {"__anyschema_metadata__": {"nullable": False, "unique": False}},
        ),
        (
            "timestamp_utc",
            SQLADateTime(timezone=True),
            (),
            {
                "__anyschema_metadata__": {
                    "nullable": True,
                    "unique": False,
                    "time_zone": "UTC",
                }
            },
        ),
        (
            "timestamp_berlin",
            SQLADateTime(timezone=True),
            (),
            {
                "__anyschema_metadata__": {
                    "nullable": True,
                    "unique": False,
                    "time_zone": "Europe/Berlin",
                    "time_unit": "ms",
                }
            },
        ),
    ]

    assert_result_equal(result, expected)
