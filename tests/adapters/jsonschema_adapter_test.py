from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Literal, Optional, Union, get_args, get_origin

import pytest
from annotated_types import Ge, Gt, Le, Lt
from typing_extensions import is_typeddict

from anyschema._dependencies import is_jsonschema
from anyschema.adapters import jsonschema_adapter
from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from anyschema.typing import FieldType


def _object(properties: dict[str, object], **extra: object) -> dict[str, object]:
    return {"type": "object", "properties": properties, **extra}


@pytest.mark.parametrize(
    ("json_type", "expected_type"),
    [
        ({"type": "string"}, str),
        ({"type": "integer"}, int),
        ({"type": "number"}, float),
        ({"type": "boolean"}, bool),
        ({"type": "string", "format": "date"}, date),
        ({"type": "string", "format": "date-time"}, datetime),
        ({"type": "string", "format": "time"}, time),
        ({"type": "string", "format": "duration"}, timedelta),
        ({"type": "string", "format": "binary"}, bytes),
        ({"type": "string", "format": "email"}, str),  # unknown format -> str
        ({"type": "string", "format": 123}, str),  # non-string format -> str
        ({"type": "array", "items": {"type": "string"}}, list[str]),
        ({"type": "array"}, list),
        # String `enum`/`const` -> `Literal` (a Narwhals `Enum`).
        ({"enum": ["a", "b"]}, Literal["a", "b"]),
        ({"const": "x"}, Literal["x"]),
        # Non-string `enum`/`const` cannot be an `Enum`, so they degrade to the underlying scalar type.
        ({"const": 5}, int),
        ({"enum": [1, 2, 3]}, int),
        ({"enum": [1.5, 2.5]}, float),
        ({"enum": [1, 2.5]}, float),  # mixed JSON numbers -> float
        ({"enum": [True, False]}, bool),
        ({"enum": [1, "a"]}, object),  # heterogeneous -> opaque object
        ({"const": [1, 2]}, object),  # non-scalar const -> opaque object
    ],
)
def test_scalar_and_generic_types(json_type: dict[str, object], expected_type: FieldType) -> None:
    spec = _object({"field": json_type})
    result = tuple(jsonschema_adapter(spec))
    assert result == (("field", expected_type, (), {}),)


@pytest.mark.parametrize(
    "spec",
    [
        _object({"x": {"anyOf": [{"type": "number"}, {"type": "null"}]}}),
        _object({"x": {"oneOf": [{"type": "number"}, {"type": "null"}]}}),
        _object({"x": {"type": ["number", "null"]}}),
    ],
)
def test_null_makes_optional(spec: dict[str, object]) -> None:
    name, field_type, constraints, metadata = next(iter(jsonschema_adapter(spec)))
    assert name == "x"
    assert field_type == Optional[float]
    assert constraints == ()
    assert metadata == {}


def test_required_does_not_drive_nullability() -> None:
    # A field absent from `required` but with no `null` type is not marked optional.
    spec = _object({"x": {"type": "string"}}, required=[])
    assert tuple(jsonschema_adapter(spec)) == (("x", str, (), {}),)


@pytest.mark.parametrize(
    ("json_schema", "expected_constraints"),
    [
        ({"type": "integer", "exclusiveMinimum": 0}, (Gt(0),)),
        ({"type": "integer", "minimum": 0, "maximum": 255}, (Ge(0), Le(255))),
        ({"type": "integer", "exclusiveMaximum": 10}, (Lt(10),)),
        ({"type": "integer"}, ()),
        ({"type": "integer", "exclusiveMinimum": True}, ()),  # legacy draft-4 boolean form is ignored
    ],
)
def test_integer_constraints_are_extracted(
    json_schema: dict[str, object], expected_constraints: tuple[object, ...]
) -> None:
    spec = _object({"n": json_schema})
    _, field_type, constraints, _ = next(iter(jsonschema_adapter(spec)))
    assert field_type is int
    assert constraints == expected_constraints


def test_integer_constraints_dropped_without_annotated_types(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("anyschema._jsonschema.ANNOTATED_TYPES_AVAILABLE", False)
    spec = _object({"age": {"type": "integer", "exclusiveMinimum": 0}})
    _, _, constraints, _ = next(iter(jsonschema_adapter(spec)))
    assert constraints == ()


def test_mixed_union_yields_union_type() -> None:
    spec = _object({"x": {"anyOf": [{"type": "integer"}, {"type": "string"}]}})
    _, field_type, _, _ = next(iter(jsonschema_adapter(spec)))
    assert field_type == Union[int, str]


def test_enum_with_null_member_is_optional() -> None:
    # A `null` member of an `enum` makes the field nullable while keeping the (string) categories.
    spec = _object({"x": {"enum": ["a", "b", None]}})
    _, field_type, _, _ = next(iter(jsonschema_adapter(spec)))
    assert field_type == Optional[Literal["a", "b"]]


def test_ref_to_nullable_union_is_resolved() -> None:
    # A `$ref` that resolves to an `anyOf`/null union must be handled, not degraded to `object`.
    spec = _object(
        {"addr": {"$ref": "#/$defs/MaybeAddress"}},
        **{
            "$defs": {
                "MaybeAddress": {"anyOf": [{"$ref": "#/$defs/Address"}, {"type": "null"}]},
                "Address": _object({"street": {"type": "string"}}),
            }
        },
    )
    _, field_type, _, _ = next(iter(jsonschema_adapter(spec)))
    assert get_origin(field_type) is Union  # Optional[<TypedDict>]
    inner, none_type = get_args(field_type)
    assert is_typeddict(inner)
    assert none_type is type(None)


@pytest.mark.parametrize(
    ("json_schema", "expected_type"),
    [
        ({}, object),  # empty schema: opaque object
        ({"type": "object"}, dict),  # object without `properties`: free-form struct
        ({"type": "null"}, Optional[object]),  # only null
    ],
)
def test_edge_case_types(json_schema: dict[str, object], expected_type: FieldType) -> None:
    spec = _object({"x": json_schema})
    _, field_type, _, _ = next(iter(jsonschema_adapter(spec)))
    assert field_type == expected_type


def test_description_is_mapped_to_metadata() -> None:
    spec = _object({"name": {"type": "string", "description": "full name"}})
    _, _, _, metadata = next(iter(jsonschema_adapter(spec)))
    assert metadata == {"anyschema": {"description": "full name"}}


def test_anyschema_namespace_is_propagated() -> None:
    spec = _object({"ts": {"type": "string", "format": "date-time", "anyschema": {"time_zone": "UTC"}}})
    _, _, _, metadata = next(iter(jsonschema_adapter(spec)))
    assert metadata == {"anyschema": {"time_zone": "UTC"}}


def test_ref_to_object_yields_typed_dict() -> None:
    spec = _object(
        {"address": {"$ref": "#/$defs/Address"}},
        **{"$defs": {"Address": _object({"street": {"type": "string"}, "zipcode": {"type": "integer"}})}},
    )
    _, field_type, _, _ = next(iter(jsonschema_adapter(spec)))
    assert is_typeddict(field_type)


def test_legacy_definitions_keyword_is_resolved() -> None:
    spec = _object(
        {"inner": {"$ref": "#/definitions/Inner"}},
        definitions={"Inner": _object({"x": {"type": "integer"}})},
    )
    _, field_type, _, _ = next(iter(jsonschema_adapter(spec)))
    assert is_typeddict(field_type)


def test_string_input_is_parsed() -> None:
    spec = json.dumps(_object({"id": {"type": "integer"}}))
    assert tuple(jsonschema_adapter(spec)) == (("id", int, (), {}),)


def test_bytes_input_is_parsed() -> None:
    spec = json.dumps(_object({"id": {"type": "integer"}})).encode()
    assert tuple(jsonschema_adapter(spec)) == (("id", int, (), {}),)


@pytest.mark.parametrize(
    "spec",
    [
        {"type": "array", "items": {"type": "string"}},  # not an object
        {"properties": {"x": {"type": "string"}}},  # missing type
        '{"type": "array"}',  # valid JSON, but not an object schema
        42,
    ],
)
def test_invalid_spec_raises_value_error(spec: object) -> None:
    with pytest.raises(ValueError, match="Expected a JSON Schema object"):
        jsonschema_adapter(spec)  # type: ignore[arg-type]


def test_malformed_json_string_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        jsonschema_adapter("not even json")


def test_unresolved_reference_raises() -> None:
    spec = _object({"x": {"$ref": "#/$defs/Missing"}})
    with pytest.raises(ValueError, match="Could not resolve JSON Schema reference"):
        tuple(jsonschema_adapter(spec))


def test_cyclic_reference_raises() -> None:
    spec = _object(
        {"node": {"$ref": "#/$defs/Node"}},
        **{"$defs": {"Node": _object({"child": {"$ref": "#/$defs/Node"}})}},
    )
    with pytest.raises(UnsupportedDTypeError, match="Recursive/cyclic"):
        tuple(jsonschema_adapter(spec))


@pytest.mark.parametrize(
    ("obj", "expected"),
    [
        ({"type": "object", "properties": {"x": {"type": "string"}}}, True),
        ({"type": "object", "properties": {}}, True),
        ({"name": int, "age": int}, False),  # plain field mapping (IntoOrderedDict)
        ({"type": "array", "items": {}}, False),
        ({"type": "object"}, False),  # no properties mapping
        ("string", False),
        (42, False),
    ],
)
def test_is_jsonschema(obj: object, *, expected: bool) -> None:
    assert is_jsonschema(obj) is expected
