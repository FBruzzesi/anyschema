from __future__ import annotations

import json

import pytest

from anyschema._dependencies import is_jsonschema
from anyschema.adapters import jsonschema_adapter
from anyschema.exceptions import UnsupportedDTypeError
from tests.conftest import json_object_schema

_ADDRESS = json_object_schema({"street": {"type": "string"}})


def test_jsonschema_adapter_yields_property_subschemas() -> None:
    spec = json_object_schema({"id": {"type": "integer"}, "tags": {"type": "array", "items": {"type": "string"}}})
    assert tuple(jsonschema_adapter(spec)) == (
        ("id", {"type": "integer"}, (), {}),
        ("tags", {"type": "array", "items": {"type": "string"}}, (), {}),
    )


@pytest.mark.parametrize("ref", ["#/$defs/Address", "#/definitions/Address"])
def test_jsonschema_adapter_inlines_refs(ref: str) -> None:
    defs_key = ref.split("/")[1]
    spec = json_object_schema({"address": {"$ref": ref}}, **{defs_key: {"Address": _ADDRESS}})
    assert tuple(jsonschema_adapter(spec)) == (("address", _ADDRESS, (), {}),)


def test_jsonschema_adapter_inlines_nested_and_chained_refs() -> None:
    spec = json_object_schema(
        {"items": {"type": "array", "items": {"anyOf": [{"$ref": "#/$defs/Alias"}, {"type": "null"}]}}},
        **{"$defs": {"Alias": {"$ref": "#/$defs/Address"}, "Address": _ADDRESS}},
    )
    _, field_type, _, _ = next(jsonschema_adapter(spec))
    assert field_type == {"type": "array", "items": {"anyOf": [_ADDRESS, {"type": "null"}]}}


def test_jsonschema_adapter_ref_siblings_take_precedence() -> None:
    spec = json_object_schema(
        {"address": {"$ref": "#/$defs/Address", "description": "home"}},
        **{"$defs": {"Address": {**_ADDRESS, "description": "an address"}}},
    )
    _, field_type, _, metadata = next(jsonschema_adapter(spec))
    assert field_type == {**_ADDRESS, "description": "home"}
    assert metadata == {"anyschema": {"description": "home"}}


def test_jsonschema_adapter_referenced_description_is_not_field_description() -> None:
    # A model docstring ends up in its `$defs` entry: it documents the model, not the field using it.
    spec = json_object_schema(
        {"address": {"$ref": "#/$defs/Address"}},
        **{"$defs": {"Address": {**_ADDRESS, "title": "Address", "description": "An address."}}},
    )
    assert tuple(jsonschema_adapter(spec)) == (("address", _ADDRESS, (), {}),)


def test_jsonschema_adapter_resolves_escaped_json_pointer() -> None:
    spec = json_object_schema({"x": {"$ref": "#/$defs/a~1b~0c"}}, **{"$defs": {"a/b~c": {"type": "integer"}}})
    assert next(jsonschema_adapter(spec))[1] == {"type": "integer"}


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        ("default", {"$ref": "https://example.com/a.json"}),
        ("examples", [{"$ref": "#/$defs/Missing"}]),
        ("const", {"$ref": "#"}),
        ("enum", [{"$ref": "#"}]),
    ],
)
def test_jsonschema_adapter_keeps_ref_in_instance_data(keyword: str, value: object) -> None:
    prop = {"type": "object", keyword: value}
    assert next(jsonschema_adapter(json_object_schema({"x": prop})))[1] == prop


def test_jsonschema_adapter_does_not_follow_additional_properties() -> None:
    # `dict[str, Node]` in a self-referencing model: `additionalProperties` is not converted, so it is not inlined.
    node = json_object_schema({}, additionalProperties={"$ref": "#/$defs/Node"})
    spec = json_object_schema({"children": {"$ref": "#/$defs/Node"}}, **{"$defs": {"Node": node}})
    assert next(jsonschema_adapter(spec))[1] == node


@pytest.mark.parametrize(
    "root",
    [{"$ref": "#/$defs/User"}, {"allOf": [{"$ref": "#/$defs/User"}]}],  # `allOf` form: Pydantic < 2.9
)
def test_jsonschema_adapter_follows_root_ref(root: dict[str, object]) -> None:
    spec = {**root, "$defs": {"User": json_object_schema({"id": {"type": "integer"}})}}
    assert tuple(jsonschema_adapter(spec)) == (("id", {"type": "integer"}, (), {}),)


def test_jsonschema_adapter_same_ref_twice_is_not_a_cycle() -> None:
    spec = json_object_schema(
        {"pair": json_object_schema({"a": {"$ref": "#/$defs/Address"}, "b": {"$ref": "#/$defs/Address"}})},
        **{"$defs": {"Address": _ADDRESS}},
    )
    assert next(jsonschema_adapter(spec))[1] == json_object_schema({"a": _ADDRESS, "b": _ADDRESS})


@pytest.mark.parametrize(
    ("prop", "expected_metadata"),
    [
        ({"type": "string", "description": "full name"}, {"anyschema": {"description": "full name"}}),
        (
            {"type": "string", "format": "date-time", "anyschema": {"time_zone": "UTC"}},
            {"anyschema": {"time_zone": "UTC"}},
        ),
        ({"type": "string", "x-anyschema": {"time_unit": "ms"}}, {"x-anyschema": {"time_unit": "ms"}}),
        # An explicit anyschema description wins over the JSON Schema keyword.
        (
            {"type": "string", "description": "json", "anyschema": {"description": "explicit"}},
            {"anyschema": {"description": "explicit"}},
        ),
        (True, {}),  # boolean subschema
    ],
)
def test_jsonschema_adapter_metadata(prop: object, expected_metadata: dict[str, object]) -> None:
    _, _, _, metadata = next(jsonschema_adapter(json_object_schema({"x": prop})))
    assert metadata == expected_metadata


def test_jsonschema_adapter_does_not_mutate_input() -> None:
    spec = json_object_schema(
        {"address": {"$ref": "#/$defs/Address"}, "name": {"type": "string", "anyschema": {"nullable": False}}},
        **{"$defs": {"Address": _ADDRESS}},
    )
    snapshot = json.dumps(spec)
    for _, _, _, metadata in jsonschema_adapter(spec):
        metadata.setdefault("anyschema", {})["unique"] = True
    assert json.dumps(spec) == snapshot


@pytest.mark.parametrize(
    "spec",
    [
        {"type": "array", "items": {"type": "string"}},
        {"type": "object"},  # no properties
        json.dumps(json_object_schema({"id": {"type": "integer"}})),  # raw JSON must be decoded first
        {"$ref": "#/$defs/Name", "$defs": {"Name": {"type": "string"}}},  # root `$ref` to a non-object
        {"allOf": [{"$ref": "#/$defs/Name"}], "$defs": {"Name": {"type": "string"}}},
        {"allOf": [True], "$defs": {}},
        42,
    ],
)
def test_jsonschema_adapter_invalid_spec_raises(spec: object) -> None:
    with pytest.raises(ValueError, match="Expected a JSON Schema object"):
        next(jsonschema_adapter(spec))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("ref", "match"),
    [
        ("#/$defs/Missing", "Could not resolve JSON Schema reference"),
        ("#/$defs/Address/type", "does not point to a schema object"),
        ("other.json#/Address", "Only local JSON Schema references"),
    ],
)
def test_jsonschema_adapter_bad_reference_raises(ref: str, match: str) -> None:
    spec = json_object_schema({"x": {"$ref": ref}}, **{"$defs": {"Address": _ADDRESS}})
    with pytest.raises(ValueError, match=match):
        next(jsonschema_adapter(spec))


@pytest.mark.parametrize(
    "spec",
    [
        json_object_schema(
            {"node": {"$ref": "#/$defs/Node"}},
            **{"$defs": {"Node": json_object_schema({"child": {"$ref": "#/$defs/Node"}})}},
        ),
        json_object_schema({"self": {"$ref": "#"}}),
        {"$ref": "#/$defs/Node", "$defs": {"Node": json_object_schema({"child": {"$ref": "#/$defs/Node"}})}},
        {
            "allOf": [{"$ref": "#/$defs/Node"}],
            "$defs": {"Node": json_object_schema({"child": {"$ref": "#/$defs/Node"}})},
        },
    ],
)
def test_jsonschema_adapter_recursive_reference_raises(spec: dict[str, object]) -> None:
    with pytest.raises(UnsupportedDTypeError, match="Recursive JSON Schema reference"):
        next(jsonschema_adapter(spec))


@pytest.mark.parametrize(
    ("obj", "expected"),
    [
        ({"type": "object", "properties": {"x": {"type": "string"}}}, True),
        ({"type": "object", "properties": {}}, True),
        ({"properties": {"x": {"type": "string"}}}, True),  # `type` is optional
        ({"$ref": "#/$defs/A", "$defs": {}}, True),  # root `$ref`
        ({"allOf": [{"$ref": "#/$defs/A"}], "$defs": {}}, True),  # root `$ref` before Pydantic 2.9
        ({"name": int, "age": int}, False),  # plain field mapping (IntoOrderedDict)
        ({"$ref": "SomeType"}, False),  # plain field mapping with a forward reference
        ({"type": "array", "items": {}}, False),
        ({"type": "array", "properties": {}}, False),
        ({"type": "object"}, False),  # no properties mapping
        ("string", False),
        (42, False),
    ],
)
def test_is_jsonschema(obj: object, *, expected: bool) -> None:
    assert is_jsonschema(obj) is expected
