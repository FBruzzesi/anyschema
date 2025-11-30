"""Tests for attrs classes as a top-level specification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Mapping, TypedDict

import attrs
import narwhals as nw
import pytest
from pydantic import BaseModel, PositiveInt

from anyschema import AnySchema

if TYPE_CHECKING:
    from anyschema.typing import AttrsClassType


@attrs.define
class PersonAttrs:
    """Simple attrs class for testing."""

    name: str
    age: int
    is_active: bool


@attrs.define
class AddressAttrs:
    """Nested attrs class for testing."""

    street: str
    city: str
    zipcode: int


@attrs.define
class PersonWithAddressAttrs:
    """Attrs class with nested attrs class for testing."""

    name: str
    age: int
    address: AddressAttrs


@attrs.define
class StudentAttrs:
    """Attrs class with list field for testing."""

    name: str
    age: int
    classes: list[str]
    grades: list[float]


@attrs.define
class UserAttrs:
    """Attrs class with Literal fields for testing."""

    username: str
    role: Literal["admin", "user", "guest"]
    status: Literal["active", "inactive", "pending"]
    age: int


@attrs.frozen
class ConfigAttrsFrozen:
    """Frozen attrs class for testing."""

    name: str
    log_level: Literal["debug", "info", "warning", "error"]
    max_retries: Literal[1, 2, 3, 5, 10]
    enabled: Literal[True, False]


class ZipcodeTypedDict(TypedDict):
    """TypedDict for testing mixed nesting."""

    zipcode: int


@attrs.define
class AddressAttrsWithTypedDict:
    """Attrs class with nested TypedDict for testing."""

    street: str
    city: str
    zipcode: ZipcodeTypedDict


class ZipcodeModel(BaseModel):
    """Pydantic model for testing mixed nesting."""

    zipcode: PositiveInt


@attrs.define
class AddressAttrsWithPydantic:
    """Attrs class with nested Pydantic model for testing."""

    street: str
    city: str
    zipcode: ZipcodeModel


@attrs.define
class BaseAttrs:
    """Base attrs class for testing inheritance."""

    id: int
    name: str


@attrs.define
class DerivedAttrs(BaseAttrs):
    """Derived attrs class for testing inheritance."""

    email: str
    is_active: bool


@pytest.mark.parametrize(
    ("spec", "expected_schema"),
    [
        (PersonAttrs, {"name": nw.String(), "age": nw.Int64(), "is_active": nw.Boolean()}),
        (
            PersonWithAddressAttrs,
            {
                "name": nw.String(),
                "age": nw.Int64(),
                "address": nw.Struct(
                    [
                        nw.Field("street", nw.String()),
                        nw.Field("city", nw.String()),
                        nw.Field("zipcode", nw.Int64()),
                    ]
                ),
            },
        ),
        (
            StudentAttrs,
            {"name": nw.String(), "age": nw.Int64(), "classes": nw.List(nw.String()), "grades": nw.List(nw.Float64())},
        ),
        (
            UserAttrs,
            {
                "username": nw.String(),
                "role": nw.Enum(["admin", "user", "guest"]),
                "status": nw.Enum(["active", "inactive", "pending"]),
                "age": nw.Int64(),
            },
        ),
        (
            ConfigAttrsFrozen,
            {
                "name": nw.String(),
                "log_level": nw.Enum(["debug", "info", "warning", "error"]),
                "max_retries": nw.Enum([1, 2, 3, 5, 10]),
                "enabled": nw.Enum([True, False]),
            },
        ),
        (
            AddressAttrsWithTypedDict,
            {
                "street": nw.String(),
                "city": nw.String(),
                "zipcode": nw.Struct([nw.Field("zipcode", nw.Int64())]),
            },
        ),
        (
            AddressAttrsWithPydantic,
            {
                "street": nw.String(),
                "city": nw.String(),
                "zipcode": nw.Struct([nw.Field("zipcode", nw.UInt64())]),
            },
        ),
        (
            DerivedAttrs,
            {
                "id": nw.Int64(),
                "name": nw.String(),
                "email": nw.String(),
                "is_active": nw.Boolean(),
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

    with pytest.raises(AssertionError, match=expected_msg.replace("(", r"\(").replace(")", r"\)")):
        AnySchema(spec=ChildWithoutDecorator)
