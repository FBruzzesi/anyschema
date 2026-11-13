from __future__ import annotations

from decimal import Decimal  # noqa: TC003 (pydantic resolves annotations at runtime)
from enum import Enum
from importlib.metadata import version
from typing import Any, Literal, Mapping

import narwhals as nw
import pytest
from narwhals.utils import parse_version
from pydantic import BaseModel, Field, PositiveInt

from anyschema import AnySchema
from anyschema.exceptions import UnsupportedDTypeError
from tests.conftest import (
    PydanticEventWithTimeMetadata,
    PydanticEventWithXAnyschema,
    PydanticStudent,
    json_object_schema,
)


@pytest.mark.parametrize(
    ("spec", "expected_schema"),
    [
        (
            json_object_schema(
                {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "score": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                    "active": {"type": "boolean"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "role": {"enum": ["admin", "user"]},
                    "age": {"type": "integer", "exclusiveMinimum": 0},
                }
            ),
            {
                "id": nw.Int64(),
                "name": nw.String(),
                "score": nw.Float64(),
                "active": nw.Boolean(),
                "tags": nw.List(nw.String()),
                "role": nw.Enum(["admin", "user"]),
                "age": nw.UInt64(),
            },
        ),
        (
            json_object_schema(
                {"address": {"$ref": "#/$defs/Address"}},
                **{
                    "$defs": {
                        "Address": json_object_schema({"street": {"type": "string"}, "zipcode": {"type": "integer"}}),
                    }
                },
            ),
            {"address": nw.Struct([nw.Field("street", nw.String()), nw.Field("zipcode", nw.Int64())])},
        ),
        (
            json_object_schema({"byte": {"type": "integer", "minimum": 0, "maximum": 255}}),
            {"byte": nw.UInt8()},
        ),
        # Integer constraints must survive inside a nested struct (regression: they were dropped).
        (
            json_object_schema(
                {"addr": json_object_schema({"zipcode": {"type": "integer", "minimum": 0, "maximum": 255}})}
            ),
            {"addr": nw.Struct([nw.Field("zipcode", nw.UInt8())])},
        ),
        # ... and inside a list's element type.
        (
            json_object_schema(
                {"bytes": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 255}}}
            ),
            {"bytes": nw.List(nw.UInt8())},
        ),
    ],
)
def test_jsonschema_to_schema(spec: dict[str, object], expected_schema: Mapping[str, nw.dtypes.DType]) -> None:
    schema = AnySchema(spec=spec)
    assert schema._nw_schema == nw.Schema(expected_schema)


def test_mixed_union_is_rejected() -> None:
    spec = json_object_schema({"x": {"anyOf": [{"type": "integer"}, {"type": "string"}]}})
    with pytest.raises(UnsupportedDTypeError, match="mixed types"):
        AnySchema(spec=spec)


@pytest.mark.parametrize(
    ("json_schema", "expected_dtype"),
    [
        ({"enum": [1, 2, 3]}, nw.Int64()),
        ({"const": 5}, nw.Int64()),
        ({"enum": [1.5, 2.5]}, nw.Float64()),
        ({"enum": [True, False]}, nw.Boolean()),
    ],
)
def test_non_string_enum_const_convert_to_backends(
    json_schema: dict[str, object], expected_dtype: nw.dtypes.DType
) -> None:
    # Non-string `enum`/`const` must degrade to a scalar dtype: a non-string `Enum` cannot be lowered to any
    # backend. These conversions would raise if the field were mapped to `Enum([...])`.
    schema = AnySchema(spec=json_object_schema({"x": json_schema}))
    assert schema._nw_schema == nw.Schema({"x": expected_dtype})
    schema.to_arrow()
    schema.to_polars()


def test_string_enum_is_polars_enum() -> None:
    # String choices stay categorical (a Narwhals `Enum`), which Polars can lower.
    import polars as pl

    schema = AnySchema(spec=json_object_schema({"role": {"enum": ["admin", "user"]}}))
    assert schema._nw_schema == nw.Schema({"role": nw.Enum(["admin", "user"])})
    assert schema.to_polars()["role"] == pl.Enum(["admin", "user"])


def test_optional_nested_model_via_anyof_ref() -> None:
    # The common Pydantic v2 emission for an optional nested model: `anyOf: [{$ref}, {"type": "null"}]`.
    spec = json_object_schema(
        {"address": {"anyOf": [{"$ref": "#/$defs/Address"}, {"type": "null"}]}},
        **{"$defs": {"Address": json_object_schema({"street": {"type": "string"}})}},
    )
    schema = AnySchema(spec=spec)
    assert schema._nw_schema == nw.Schema({"address": nw.Struct([nw.Field("street", nw.String())])})
    assert schema.nullables(named=True) == {"address": True}


def test_jsonschema_dict_is_not_treated_as_field_mapping() -> None:
    # A JSON Schema is also a `Mapping`; it must be detected before the `IntoOrderedDict` adapter.
    spec = json_object_schema({"id": {"type": "integer"}, "name": {"type": "string"}})
    schema = AnySchema(spec=spec)
    assert schema.names() == ("id", "name")


def test_nullable_and_description_propagate() -> None:
    spec = json_object_schema(
        {
            "email": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "contact email"},
            "id": {"type": "integer"},
        }
    )
    schema = AnySchema(spec=spec)
    assert schema.nullables(named=True) == {"email": True, "id": False}
    assert schema.descriptions(named=True) == {"email": "contact email", "id": None}


def test_plain_mapping_with_nested_dict_is_not_a_jsonschema() -> None:
    # A nested mapping that is not a JSON Schema must still fail instead of becoming an Object column.
    with pytest.raises(NotImplementedError, match="No parser in the pipeline could handle"):
        AnySchema(spec={"x": {"b": int}})


class _RoundTripAddress(BaseModel):
    """A postal address."""

    zipcode: PositiveInt  # nested constrained int -> must round-trip to UInt64, not Int64
    street: str


class _RoundTripColor(str, Enum):
    """A color."""

    RED = "red"
    BLUE = "blue"


class _RoundTripModel(BaseModel):
    """Exercises the nested-constraint, list-of-constrained, enum and optional paths together."""

    id: PositiveInt
    tags: list[str]
    role: Literal["admin", "user"]
    address: _RoundTripAddress
    nickname: str | None
    scores: list[PositiveInt]
    pair: tuple[int, int]
    maybe_address: _RoundTripAddress | None
    color: _RoundTripColor
    price: Decimal
    maybe_price: Decimal | None
    retries: int = 5
    note: str | None = None


class _RoundTripLink(BaseModel):
    """Instance data that looks like a `$ref` is not a reference."""

    target: dict[str, Any] = Field(default={"$ref": "https://example.com/a.json"})


class _RoundTripTree(BaseModel):
    """Self-referencing model: its JSON Schema has a root `$ref`, and the recursion sits in `dict` values."""

    name: str
    children: dict[str, _RoundTripTree]


_ROUND_TRIP_MODELS: list[type[BaseModel] | Any] = [
    PydanticStudent,
    PydanticEventWithTimeMetadata,
    PydanticEventWithXAnyschema,
    _RoundTripModel,
    pytest.param(
        _RoundTripLink,
        marks=pytest.mark.skipif(
            parse_version(version("pydantic")) < (2, 9), reason="`model_json_schema()` raises on a `$ref` default"
        ),
    ),
    _RoundTripTree,
]


@pytest.mark.parametrize("model", _ROUND_TRIP_MODELS)
def test_pydantic_json_schema_round_trip(model: type[BaseModel]) -> None:
    # Reconstructing an `AnySchema` from a model's JSON schema matches building it from the model itself.
    from_model = AnySchema(spec=model)
    from_json = AnySchema(spec=model.model_json_schema())
    assert from_json == from_model


class _RecursiveNode(BaseModel):
    child: _RecursiveNode | None = None


def test_recursive_model_json_schema_is_rejected() -> None:
    with pytest.raises(UnsupportedDTypeError, match="Recursive JSON Schema reference"):
        AnySchema(spec=_RecursiveNode.model_json_schema())
