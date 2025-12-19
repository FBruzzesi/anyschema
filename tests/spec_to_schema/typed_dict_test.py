from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Mapping, TypedDict

import narwhals as nw
import pytest
from pydantic import BaseModel, PositiveInt

from anyschema import AnySchema

if TYPE_CHECKING:
    from anyschema.typing import TypedDictType


class PersonTypedDict(TypedDict):
    """Simple TypedDict for testing."""

    name: str
    age: int
    is_active: bool


class AddressTypedDict(TypedDict):
    """Nested TypedDict for testing."""

    street: str
    city: str
    zipcode: int


class PersonWithAddressTypedDict(TypedDict):
    """TypedDict with nested TypedDict for testing."""

    name: str
    age: int
    address: AddressTypedDict


class StudentTypedDict(TypedDict):
    """TypedDict with list field for testing."""

    name: str
    age: int
    classes: list[str]
    grades: list[float]


class UserTypedDict(TypedDict):
    """TypedDict with Literal fields for testing."""

    username: str
    role: Literal["admin", "user", "guest"]
    status: Literal["active", "inactive", "pending"]
    age: int


class ConfigTypedDict(TypedDict):
    """TypedDict with mixed Literal types for testing."""

    name: str
    log_level: Literal["debug", "info", "warning", "error"]
    max_retries: Literal[1, 2, 3, 5, 10]
    enabled: Literal[True, False]


class ZipcodeModel(BaseModel):
    zipcode: PositiveInt


class AddressTypedDictWithZipcodeModel(TypedDict):
    """TypedDict with Nested pydantic model for testing."""

    street: str
    city: str
    zipcode: ZipcodeModel


@pytest.mark.parametrize(
    ("spec", "expected_schema"),
    [
        (PersonTypedDict, {"name": nw.String(), "age": nw.Int64(), "is_active": nw.Boolean()}),
        (
            PersonWithAddressTypedDict,
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
            StudentTypedDict,
            {"name": nw.String(), "age": nw.Int64(), "classes": nw.List(nw.String()), "grades": nw.List(nw.Float64())},
        ),
        (
            UserTypedDict,
            {
                "username": nw.String(),
                "role": nw.Enum(["admin", "user", "guest"]),
                "status": nw.Enum(["active", "inactive", "pending"]),
                "age": nw.Int64(),
            },
        ),
        (
            ConfigTypedDict,
            {
                "name": nw.String(),
                "log_level": nw.Enum(["debug", "info", "warning", "error"]),
                "max_retries": nw.Enum([1, 2, 3, 5, 10]),  # type: ignore[list-item]
                "enabled": nw.Enum([True, False]),  # type: ignore[list-item]
            },
        ),
        (
            AddressTypedDictWithZipcodeModel,
            {
                "street": nw.String(),
                "city": nw.String(),
                "zipcode": nw.Struct([nw.Field("zipcode", nw.UInt64())]),
            },
        ),
    ],
)
def test_typed_dict(spec: TypedDictType, expected_schema: Mapping[str, nw.dtypes.DType]) -> None:
    schema = AnySchema(spec=spec)
    nw_schema = schema._nw_schema
    assert nw_schema == nw.Schema(expected_schema)
