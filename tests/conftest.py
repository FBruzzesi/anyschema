from __future__ import annotations

from datetime import date  # noqa: TC003
from typing import TYPE_CHECKING, Literal

import attrs
import narwhals as nw
import pytest
from pydantic import BaseModel, PastDate, PositiveInt

from anyschema._dependencies import SQLALCHEMY_AVAILABLE
from anyschema.parsers import make_pipeline

if TYPE_CHECKING:
    from anyschema.parsers import ParserPipeline


@pytest.fixture(scope="session")
def auto_pipeline() -> ParserPipeline:
    """Fixture to get the auto pipeline."""
    return make_pipeline("auto")


@pytest.fixture
def nw_schema() -> nw.Schema:
    return nw.Schema(
        {
            "array": nw.Array(nw.Int32(), 3),
            "boolean": nw.Boolean(),
            "categorical": nw.Categorical(),
            "date": nw.Date(),
            "datetime": nw.Datetime(),
            "decimal": nw.Decimal(),
            "duration": nw.Duration(),
            "enum": nw.Enum(["foo", "bar"]),
            "float32": nw.Float32(),
            "float64": nw.Float64(),
            "int8": nw.Int8(),
            "int16": nw.Int16(),
            "int32": nw.Int32(),
            "int64": nw.Int64(),
            "int128": nw.Int128(),
            "list": nw.List(nw.Float32()),
            "object": nw.Object(),
            "string": nw.String(),
            "struct": nw.Struct(fields=[nw.Field("field_1", nw.String()), nw.Field("field_2", nw.Boolean())]),
            "uint8": nw.UInt8(),
            "uint16": nw.UInt16(),
            "uint32": nw.UInt32(),
            "uint64": nw.UInt64(),
            "uint128": nw.UInt128(),
            "unknown": nw.Unknown(),
        }
    )


class PydanticStudent(BaseModel):
    name: str
    date_of_birth: PastDate
    age: PositiveInt
    classes: list[str]
    has_graduated: bool


@pytest.fixture(scope="session")
def pydantic_student_cls() -> type[PydanticStudent]:
    return PydanticStudent


@attrs.define
class AttrsAddress:
    street: str
    city: str


@attrs.define
class AttrsPerson:
    name: str
    age: int
    date_of_birth: date
    is_active: bool
    classes: list[str]
    grades: list[float]


@attrs.frozen
class AttrsPersonFrozen:
    name: str
    age: int
    date_of_birth: date


@attrs.define
class AttrsBase:
    foo: str
    bar: int


@attrs.define
class AttrsDerived(AttrsBase):
    baz: float


@attrs.define
class AttrsBookWithMetadata:
    title: str = attrs.field(metadata={"description": "Book title"})
    author: str = attrs.field(metadata={"max_length": 100})


@attrs.define
class AttrsPersonWithLiterals:
    username: str
    role: Literal["admin", "user", "guest"]
    status: Literal["active", "inactive", "pending"]


class PydanticZipcode(BaseModel):
    zipcode: PositiveInt


@attrs.define
class AttrsAddressWithPydantic:
    street: str
    city: str
    zipcode: PydanticZipcode


def create_missing_decorator_test_case() -> tuple[type, str]:
    """Create a test case for missing decorator inheritance issue.

    Returns:
        A tuple of (child_class, expected_error_message) for testing.
    """

    @attrs.define
    class Base:
        foo: str

    class ChildWithoutDecorator(Base):
        bar: int

    expected_msg = (
        "Class 'ChildWithoutDecorator' has annotations ('bar') that are not attrs fields. "
        "If this class inherits from an attrs class, you must also decorate it with @attrs.define "
        "or @attrs.frozen to properly define these fields."
    )

    return ChildWithoutDecorator, expected_msg


# SQLAlchemy fixtures (only created if SQLAlchemy is available)
if SQLALCHEMY_AVAILABLE:
    from sqlalchemy import ARRAY, BigInteger, Boolean, Column, Date, DateTime, Float, Integer, MetaData, String, Table
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

    class SQLAlchemyBase(DeclarativeBase):
        pass

    class SimpleUserORM(SQLAlchemyBase):
        __tablename__ = "simple_user"
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str | None]

    class UserWithTypesORM(SQLAlchemyBase):
        __tablename__ = "user_with_types"
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column(String(50))
        age: Mapped[int] = mapped_column(Integer, nullable=True)
        score: Mapped[float | None]

    class ProductORM(SQLAlchemyBase):
        """ORM model with multiple field types for testing."""

        __tablename__ = "product_orm"
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str]
        price: Mapped[float]
        in_stock: Mapped[bool]

    class ComplexORM(SQLAlchemyBase):
        """ORM model with various column types for testing."""

        __tablename__ = "complex_orm"
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column(String(50))
        description: Mapped[str]
        age: Mapped[int]
        score: Mapped[float] = mapped_column(Float)
        is_active: Mapped[bool]
        created_at: Mapped[DateTime] = mapped_column(DateTime)
        birth_date: Mapped[Date] = mapped_column(Date)

    # Core Table instances
    metadata = MetaData()

    user_table = Table(
        "user",
        metadata,
        Column("id", Integer, primary_key=True, nullable=False),
        Column("name", String(50)),
        Column("age", Integer),
        Column("email", String(100), nullable=True),
    )

    numeric_table = Table(
        "numeric_table",
        metadata,
        Column("int_col", Integer),
        Column("bigint_col", BigInteger),
        Column("string_col", String(100)),
        Column("float_col", Float),
    )

    complex_table = Table(
        "complex_table",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50)),
        Column("description", String),
        Column("age", Integer),
        Column("score", Float),
        Column("is_active", Boolean),
        Column("created_at", DateTime),
        Column("birth_date", Date),
    )

    bigint_table = Table(
        "bigint_table",
        metadata,
        Column("id", BigInteger, primary_key=True),
        Column("count", BigInteger),
    )

    array_list_table = Table(
        "array_list_table",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("tags", ARRAY(String)),
        Column("scores", ARRAY(Float)),
    )

    array_fixed_table = Table(
        "array_fixed_table",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("coordinates", ARRAY(Float, dimensions=3)),
        Column("matrix", ARRAY(Integer, dimensions=2)),
    )
