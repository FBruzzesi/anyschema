from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import BigInteger, Float, Integer, String
from sqlalchemy.types import TypeEngine

from anyschema.adapters import sqlalchemy_adapter
from tests.conftest import SimpleUserORM, UserWithTypesORM, numeric_table, user_table

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
                ("id", Integer(), (), {"anyschema/nullable": False, "anyschema/unique": False}),
                ("name", String(), (), {"anyschema/nullable": True, "anyschema/unique": False}),
            ],
        ),
        (
            UserWithTypesORM,
            [
                ("id", Integer(), (), {"anyschema/nullable": False, "anyschema/unique": False}),
                ("name", String(50), (), {"anyschema/nullable": False, "anyschema/unique": False}),
                ("age", Integer(), (), {"anyschema/nullable": True, "anyschema/unique": False}),
                ("score", Float(), (), {"anyschema/nullable": True, "anyschema/unique": False}),
            ],
        ),
        (
            user_table,
            [
                ("id", Integer(), (), {"anyschema/nullable": False, "anyschema/unique": False}),
                ("name", String(50), (), {"anyschema/nullable": True, "anyschema/unique": False}),
                ("age", Integer(), (), {"anyschema/nullable": True, "anyschema/unique": False}),
                ("email", String(100), (), {"anyschema/nullable": True, "anyschema/unique": False}),
            ],
        ),
        (
            numeric_table,
            [
                ("int_col", Integer(), (), {"anyschema/nullable": True, "anyschema/unique": False}),
                ("bigint_col", BigInteger(), (), {"anyschema/nullable": True, "anyschema/unique": False}),
                ("string_col", String(100), (), {"anyschema/nullable": True, "anyschema/unique": False}),
                ("float_col", Float(), (), {"anyschema/nullable": True, "anyschema/unique": False}),
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
