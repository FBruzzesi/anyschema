"""Tests for TypedDict as a top-level specification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, TypedDict

import narwhals as nw
import pytest

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
    ],
)
def test_typed_dict(spec: TypedDictType, expected_schema: Mapping[str, nw.dtypes.DType]) -> None:
    schema = AnySchema(spec=spec)
    nw_schema = schema._nw_schema
    assert nw_schema == nw.Schema(expected_schema)
