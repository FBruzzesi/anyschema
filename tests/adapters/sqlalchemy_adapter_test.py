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
        (SimpleUserORM, [("id", Integer(), (False,)), ("name", String(), (True,))]),
        (
            UserWithTypesORM,
            [
                ("id", Integer(), (False,)),
                ("name", String(50), (False,)),
                ("age", Integer(), (True,)),
                ("score", Float(), (True,)),
            ],
        ),
        (
            user_table,
            [
                ("id", Integer(), (False,)),
                ("name", String(50), (True,)),
                ("age", Integer(), (True,)),
                ("email", String(100), (True,)),
            ],
        ),
        (
            numeric_table,
            [
                ("int_col", Integer(), (True,)),
                ("bigint_col", BigInteger(), (True,)),
                ("string_col", String(100), (True,)),
                ("float_col", Float(), (True,)),
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
