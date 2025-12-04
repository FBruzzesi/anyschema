from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
import narwhals as nw
import pytest
from pydantic import BaseModel, PastDate, PositiveInt

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
    address: AttrsAddress


@attrs.define
class AttrsBase:
    foo: str
    bar: int


@attrs.define
class AttrsDerived(AttrsBase):
    baz: float


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
