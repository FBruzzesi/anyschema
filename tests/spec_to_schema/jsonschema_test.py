from __future__ import annotations

import json
from typing import Literal, Mapping

import narwhals as nw
import pytest
from pydantic import BaseModel, PositiveInt

from anyschema import AnySchema
from anyschema.adapters import jsonschema_adapter
from anyschema.exceptions import UnsupportedDTypeError
from tests.conftest import (
    PydanticEventWithTimeMetadata,
    PydanticEventWithXAnyschema,
    PydanticStudent,
)


def _object(properties: dict[str, object], **extra: object) -> dict[str, object]:
    return {"type": "object", "properties": properties, **extra}


@pytest.mark.parametrize(
    ("spec", "expected_schema"),
    [
        (
            _object(
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
            _object(
                {"address": {"$ref": "#/$defs/Address"}},
                **{
                    "$defs": {
                        "Address": _object({"street": {"type": "string"}, "zipcode": {"type": "integer"}}),
                    }
                },
            ),
            {"address": nw.Struct([nw.Field("street", nw.String()), nw.Field("zipcode", nw.Int64())])},
        ),
        (
            _object({"byte": {"type": "integer", "minimum": 0, "maximum": 255}}),
            {"byte": nw.UInt8()},
        ),
        # Integer constraints must survive inside a nested struct (regression: they were dropped).
        (
            _object({"addr": _object({"zipcode": {"type": "integer", "minimum": 0, "maximum": 255}})}),
            {"addr": nw.Struct([nw.Field("zipcode", nw.UInt8())])},
        ),
        # ... and inside a list's element type.
        (
            _object({"bytes": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 255}}}),
            {"bytes": nw.List(nw.UInt8())},
        ),
    ],
)
def test_jsonschema_to_schema(spec: dict[str, object], expected_schema: Mapping[str, nw.dtypes.DType]) -> None:
    schema = AnySchema(spec=spec)
    assert schema._nw_schema == nw.Schema(expected_schema)


def test_mixed_union_is_rejected() -> None:
    spec = _object({"x": {"anyOf": [{"type": "integer"}, {"type": "string"}]}})
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
    schema = AnySchema(spec=_object({"x": json_schema}))
    assert schema._nw_schema == nw.Schema({"x": expected_dtype})
    schema.to_arrow()
    schema.to_polars()


def test_string_enum_is_polars_enum() -> None:
    # String choices stay categorical (a Narwhals `Enum`), which Polars can lower.
    import polars as pl

    schema = AnySchema(spec=_object({"role": {"enum": ["admin", "user"]}}))
    assert schema._nw_schema == nw.Schema({"role": nw.Enum(["admin", "user"])})
    assert schema.to_polars()["role"] == pl.Enum(["admin", "user"])


def test_optional_nested_model_via_anyof_ref() -> None:
    # The common Pydantic v2 emission for an optional nested model: `anyOf: [{$ref}, {"type": "null"}]`.
    spec = _object(
        {"address": {"anyOf": [{"$ref": "#/$defs/Address"}, {"type": "null"}]}},
        **{"$defs": {"Address": _object({"street": {"type": "string"}})}},
    )
    schema = AnySchema(spec=spec)
    assert schema._nw_schema == nw.Schema({"address": nw.Struct([nw.Field("street", nw.String())])})
    assert schema.nullables(named=True) == {"address": True}


def test_jsonschema_dict_is_not_treated_as_field_mapping() -> None:
    # A JSON Schema is also a `Mapping`; it must be detected before the `IntoOrderedDict` adapter.
    spec = _object({"id": {"type": "integer"}, "name": {"type": "string"}})
    schema = AnySchema(spec=spec)
    assert schema.names() == ("id", "name")


def test_nullable_and_description_propagate() -> None:
    spec = _object(
        {
            "email": {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "contact email"},
            "id": {"type": "integer"},
        }
    )
    schema = AnySchema(spec=spec)
    assert schema.nullables(named=True) == {"email": True, "id": False}
    assert schema.descriptions(named=True) == {"email": "contact email", "id": None}


def test_string_spec_via_explicit_adapter() -> None:
    # Raw JSON strings are not auto-detected, but can be passed through the adapter argument.
    spec = json.dumps(_object({"id": {"type": "integer"}, "name": {"type": "string"}}))
    schema = AnySchema(spec=spec, adapter=jsonschema_adapter)
    assert schema._nw_schema == nw.Schema({"id": nw.Int64(), "name": nw.String()})


class _RoundTripAddress(BaseModel):
    zipcode: PositiveInt  # nested constrained int -> must round-trip to UInt64, not Int64
    street: str


class _RoundTripModel(BaseModel):
    """Exercises the nested-constraint, list-of-constrained, enum and optional paths together."""

    id: PositiveInt
    tags: list[str]
    role: Literal["admin", "user"]
    address: _RoundTripAddress
    nickname: str | None
    scores: list[PositiveInt]


_ROUND_TRIP_MODELS: list[type[BaseModel]] = [
    PydanticStudent,
    PydanticEventWithTimeMetadata,
    PydanticEventWithXAnyschema,
    _RoundTripModel,
]


@pytest.mark.parametrize("model", _ROUND_TRIP_MODELS)
def test_pydantic_json_schema_round_trip(model: type[BaseModel]) -> None:
    # Reconstructing an `AnySchema` from a model's JSON schema matches building it from the model itself.
    from_model = AnySchema(spec=model)
    from_json = AnySchema(spec=model.model_json_schema())
    assert from_json == from_model
