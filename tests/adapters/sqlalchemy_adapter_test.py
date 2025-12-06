from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import BigInteger, Column, Float, Integer, MetaData, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeEngine

from anyschema.adapters import sqlalchemy_adapter

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


class Base(DeclarativeBase):
    pass


class SimpleUser(Base):
    __tablename__ = "simple_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None]


class UserWithTypes(Base):
    __tablename__ = "user_with_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None]


user_table = Table(
    "user",
    MetaData(),
    Column("id", Integer, primary_key=True, nullable=False),
    Column("name", String(50)),
    Column("age", Integer),
    Column("email", String(100), nullable=True),
)

numeric_table = Table(
    "numeric_table",
    MetaData(),
    Column("int_col", Integer),
    Column("bigint_col", BigInteger),
    Column("string_col", String(100)),
    Column("float_col", Float),
)


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (SimpleUser, [("id", Integer(), (False,)), ("name", String(), (True,))]),
        (
            UserWithTypes,
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
