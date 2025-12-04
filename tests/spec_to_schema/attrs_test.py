"""Tests for attrs classes as a top-level specification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Mapping

import attrs
import narwhals as nw
import pytest
from pydantic import BaseModel, PositiveInt

from anyschema import AnySchema
from tests.conftest import AttrsDerived, create_missing_decorator_test_case

if TYPE_CHECKING:
    from anyschema.typing import AttrsClassType


@attrs.define
class AttrsPerson:
    """Simple attrs class for testing."""

    name: str
    age: int
    is_active: bool


@attrs.define
class AttrsPersonWithLists:
    """Attrs class with list field for testing."""

    name: str
    classes: list[str]
    grades: list[float]


@attrs.define
class AttrsPersonWithLiterals:
    """Attrs class with Literal fields for testing."""

    username: str
    role: Literal["admin", "user", "guest"]
    status: Literal["active", "inactive", "pending"]


class ZipcodeModel(BaseModel):
    """Pydantic model for testing mixed nesting."""

    zipcode: PositiveInt


@attrs.define
class AttrsAddressWithPydantic:
    """Attrs class with nested Pydantic model for testing."""

    street: str
    city: str
    zipcode: ZipcodeModel


@pytest.mark.parametrize(
    ("spec", "expected_schema"),
    [
        (AttrsPerson, {"name": nw.String(), "age": nw.Int64(), "is_active": nw.Boolean()}),
        (
            AttrsPersonWithLists,
            {"name": nw.String(), "classes": nw.List(nw.String()), "grades": nw.List(nw.Float64())},
        ),
        (
            AttrsPersonWithLiterals,
            {
                "username": nw.String(),
                "role": nw.Enum(["admin", "user", "guest"]),
                "status": nw.Enum(["active", "inactive", "pending"]),
            },
        ),
        (
            AttrsAddressWithPydantic,
            {
                "street": nw.String(),
                "city": nw.String(),
                "zipcode": nw.Struct([nw.Field("zipcode", nw.UInt64())]),
            },
        ),
        (
            AttrsDerived,
            {
                "foo": nw.String(),
                "bar": nw.Int64(),
                "baz": nw.Float64(),
            },
        ),
    ],
)
def test_attrs_class(spec: AttrsClassType, expected_schema: Mapping[str, nw.dtypes.DType]) -> None:
    schema = AnySchema(spec=spec)
    nw_schema = schema._nw_schema
    assert nw_schema == nw.Schema(expected_schema)


def test_attrs_class_missing_decorator_raises() -> None:
    """Test that AnySchema raises helpful error when child class isn't decorated."""
    child_cls, expected_msg = create_missing_decorator_test_case()
    with pytest.raises(AssertionError, match=expected_msg.replace("(", r"\(").replace(")", r"\)")):
        AnySchema(spec=child_cls)
