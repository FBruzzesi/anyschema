from __future__ import annotations

import json
from typing import TYPE_CHECKING, Mapping

import narwhals as nw
import pytest

from anyschema import AnySchema
from anyschema.adapters import jsonschema_adapter
from anyschema.exceptions import UnsupportedDTypeError
from tests.conftest import (
    PydanticEventWithTimeMetadata,
    PydanticEventWithXAnyschema,
    PydanticStudent,
)

if TYPE_CHECKING:
    from pydantic import BaseModel


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
    ],
)
def test_jsonschema_to_schema(spec: dict[str, object], expected_schema: Mapping[str, nw.dtypes.DType]) -> None:
    schema = AnySchema(spec=spec)
    assert schema._nw_schema == nw.Schema(expected_schema)


def test_mixed_union_is_rejected() -> None:
    spec = _object({"x": {"anyOf": [{"type": "integer"}, {"type": "string"}]}})
    with pytest.raises(UnsupportedDTypeError, match="mixed types"):
        AnySchema(spec=spec)


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


_ROUND_TRIP_MODELS: list[type[BaseModel]] = [
    PydanticStudent,
    PydanticEventWithTimeMetadata,
    PydanticEventWithXAnyschema,
]


@pytest.mark.parametrize("model", _ROUND_TRIP_MODELS)
def test_pydantic_json_schema_round_trip(model: type[BaseModel]) -> None:
    # Reconstructing an `AnySchema` from a model's JSON schema matches building it from the model itself.
    from_model = AnySchema(spec=model)
    from_json = AnySchema(spec=model.model_json_schema())
    assert from_json == from_model
