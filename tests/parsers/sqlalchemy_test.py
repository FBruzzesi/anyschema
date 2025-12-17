from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING, Any

import narwhals as nw
import pytest
from sqlalchemy import types as sqltypes

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers import make_pipeline
from anyschema.parsers.sqlalchemy import SQLAlchemyTypeStep

if TYPE_CHECKING:
    from narwhals.typing import TimeUnit


@pytest.fixture
def sqlalchemy_step() -> SQLAlchemyTypeStep:
    """Create a SQLAlchemyTypeStep with pipeline."""
    step = SQLAlchemyTypeStep()
    _ = make_pipeline(steps=[step])
    return step


class Color(Enum):
    RED = 1
    BLUE = 2


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (sqltypes.Boolean(), nw.Boolean()),
        (sqltypes.SmallInteger(), nw.Int16()),
        (sqltypes.Integer(), nw.Int32()),
        (sqltypes.BigInteger(), nw.Int64()),
        (sqltypes.String(50), nw.String()),
        (sqltypes.Text(), nw.String()),
        (sqltypes.Unicode(50), nw.String()),
        (sqltypes.UnicodeText(), nw.String()),
        (sqltypes.Float(), nw.Float32()),
        (sqltypes.Double(), nw.Float64()),
        (sqltypes.Numeric(10, 2), nw.Float64()),
        (sqltypes.DECIMAL(10, 2), nw.Decimal()),
        (sqltypes.Date(), nw.Date()),
        (sqltypes.DateTime(), nw.Datetime()),
        (sqltypes.TIMESTAMP(), nw.Datetime()),
        (sqltypes.Time(), nw.Time()),
        (sqltypes.Interval(), nw.Duration()),
        (sqltypes.LargeBinary(), nw.Binary()),
        (sqltypes.BINARY(), nw.Binary()),
        (sqltypes.VARBINARY(), nw.Binary()),
        (sqltypes.JSON(), nw.String()),
        (sqltypes.Uuid(), nw.String()),
        (sqltypes.Enum("red", "green", "blue"), nw.Enum(["red", "green", "blue"])),
        (sqltypes.Enum(Color), nw.Enum(Color)),
        (sqltypes.ARRAY(sqltypes.Float()), nw.List(nw.Float32())),
        (sqltypes.ARRAY(sqltypes.Float(), dimensions=3), nw.Array(nw.Float32(), shape=(3,))),
        (int, None),
        ("not a sqlalchemy type", None),
    ],
)
def test_sqlalchemy_parse_step(sqlalchemy_step: SQLAlchemyTypeStep, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = sqlalchemy_step.parse(input_type=input_type, constraints=(), metadata={})
    assert result == expected


@pytest.mark.parametrize("time_unit", ["s", "ms", "ns", "us"])
def test_sqlalchemy_datetime_naive_with_time_unit_metadata(
    sqlalchemy_step: SQLAlchemyTypeStep, time_unit: TimeUnit
) -> None:
    result = sqlalchemy_step.parse(
        input_type=sqltypes.DateTime(), constraints=(), metadata={"__anyschema_metadata__": {"time_unit": time_unit}}
    )
    assert result == nw.Datetime(time_unit)


def test_sqlalchemy_datetime_tz_aware_without_metadata_raises(sqlalchemy_step: SQLAlchemyTypeStep) -> None:
    msg = re.escape("SQLAlchemy `DateTime(timezone=True)` does not specify a fixed timezone.")
    with pytest.raises(UnsupportedDTypeError, match=msg):
        sqlalchemy_step.parse(input_type=sqltypes.DateTime(timezone=True), constraints=(), metadata={})


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({"__anyschema_metadata__": {"time_zone": "UTC"}}, nw.Datetime("us", time_zone="UTC")),
        ({"__anyschema_metadata__": {"time_zone": "Europe/Rome"}}, nw.Datetime("us", time_zone="Europe/Rome")),
        ({"__anyschema_metadata__": {"time_unit": "ms", "time_zone": "UTC"}}, nw.Datetime("ms", time_zone="UTC")),
        (
            {"__anyschema_metadata__": {"time_unit": "ns", "time_zone": "America/New_York"}},
            nw.Datetime("ns", time_zone="America/New_York"),
        ),
    ],
)
def test_sqlalchemy_datetime_tz_aware_with_metadata(
    sqlalchemy_step: SQLAlchemyTypeStep, metadata: dict[str, Any], expected: nw.dtypes.DType
) -> None:
    result = sqlalchemy_step.parse(
        input_type=sqltypes.DateTime(timezone=True),
        constraints=(),
        metadata=metadata,
    )
    assert result == expected


def test_sqlalchemy_datetime_naive_with_timezone_raises(sqlalchemy_step: SQLAlchemyTypeStep) -> None:
    msg = re.escape("SQLAlchemy `DateTime(timezone=False)` should not specify a fixed timezone, found UTC")
    with pytest.raises(Exception, match=msg):
        sqlalchemy_step.parse(
            input_type=sqltypes.DateTime(timezone=False),
            constraints=(),
            metadata={"__anyschema_metadata__": {"time_zone": "UTC"}},
        )


@pytest.mark.parametrize("input_type", [int, str, list[int], dict])
def test_sqlalchemy_non_sqlalchemy_types_return_none(sqlalchemy_step: SQLAlchemyTypeStep, input_type: Any) -> None:
    result = sqlalchemy_step.parse(input_type=input_type, constraints=(), metadata={})
    assert result is None


@pytest.mark.parametrize(
    "input_type",
    [
        sqltypes.PickleType(),
        sqltypes.NullType(),
    ],
)
def test_sqlalchemy_unhandled_types_return_none(sqlalchemy_step: SQLAlchemyTypeStep, input_type: Any) -> None:
    result = sqlalchemy_step.parse(input_type=input_type, constraints=(), metadata={})
    assert result is None
