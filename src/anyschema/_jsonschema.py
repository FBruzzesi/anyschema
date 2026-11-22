"""JSON Schema helpers shared by `jsonschema_adapter` and `JsonSchemaStep`."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Final

from anyschema._metadata import get_anyschema_value_by_key, set_anyschema_meta

if TYPE_CHECKING:
    from anyschema.typing import FieldMetadata, JsonSchema

__all__ = ("allows_null", "extract_field_metadata", "inline_refs", "union_branches")

_SUBSCHEMA_KEYWORDS: Final = frozenset({"items", "prefixItems", "anyOf", "oneOf", "allOf"})
"""Keywords holding a subschema or a list of subschemas that `JsonSchemaStep` reads, besides `properties`.

Other keywords are copied as-is: `default`, `examples`, `const` and `enum` hold instance data, which may contain a
literal `"$ref"` key, and `additionalProperties` is not converted.
"""

_DEFINITION_DOC_KEYWORDS: Final = frozenset({"title", "description"})
"""Keywords of a referenced definition that describe the definition, not the field pointing to it."""

_UNION_KEYWORDS: Final = ("anyOf", "oneOf", "allOf")


def inline_refs(schema: JsonSchema, root: JsonSchema, _expanding: tuple[str, ...] = ()) -> JsonSchema:
    """Return a copy of `schema` with every local `$ref` replaced by the definition it points to.

    Keywords next to a `$ref` override the referenced ones. The referenced `title` and `description` are dropped, so
    a model docstring does not become the description of every field of that model type. A recursive `$ref` is kept
    as is, for `JsonSchemaStep` to reject unless the field sets a `dtype`.

    Arguments:
        schema: The (sub)schema to resolve.
        root: The document that `$ref` pointers are resolved against.
        _expanding: The `$ref`s being expanded on the current path, used to detect cycles.

    Raises:
        ValueError: If a `$ref` is not local (`#...`) or cannot be resolved.
    """
    if isinstance(ref := schema.get("$ref"), str):
        if ref in _expanding:
            return schema
        definition = _resolve_json_pointer(root, ref)
        merged = {key: value for key, value in definition.items() if key not in _DEFINITION_DOC_KEYWORDS}
        merged.update((key, value) for key, value in schema.items() if key != "$ref")
        return inline_refs(merged, root, (*_expanding, ref))

    inlined = dict(schema)
    if isinstance(properties := schema.get("properties"), Mapping):
        inlined["properties"] = {name: _inline_subschemas(sub, root, _expanding) for name, sub in properties.items()}
    for keyword in _SUBSCHEMA_KEYWORDS & schema.keys():
        inlined[keyword] = _inline_subschemas(schema[keyword], root, _expanding)
    return inlined


def _inline_subschemas(value: Any, root: JsonSchema, expanding: tuple[str, ...]) -> Any:
    """Inline refs in a subschema or a list of subschemas. Boolean subschemas are returned unchanged."""
    if isinstance(value, Mapping):
        return inline_refs(value, root, expanding)
    if isinstance(value, list):
        return [_inline_subschemas(item, root, expanding) for item in value]
    return value


def _resolve_json_pointer(root: JsonSchema, ref: str) -> JsonSchema:
    """Resolve a local JSON pointer such as `#/$defs/Address` against `root`."""
    if ref != "#" and not ref.startswith("#/"):
        msg = f"Only local JSON Schema references (starting with '#') are supported, found: {ref!r}."
        raise ValueError(msg)

    target: Any = root
    for token in ref[2:].split("/") if ref != "#" else ():
        key = token.replace("~1", "/").replace("~0", "~")  # RFC 6901 escaping
        if not isinstance(target, Mapping) or key not in target:
            msg = f"Could not resolve JSON Schema reference: {ref!r}."
            raise ValueError(msg)
        target = target[key]

    if not isinstance(target, Mapping):
        msg = f"JSON Schema reference {ref!r} does not point to a schema object."
        raise ValueError(msg)  # noqa: TRY004
    return target


def extract_field_metadata(schema: object) -> FieldMetadata:
    """Build field metadata from a property subschema.

    Copies the `anyschema` and `x-anyschema` namespaces, and maps `description` to the anyschema description unless a
    namespace already sets one. Boolean subschemas carry no metadata.
    """
    if not isinstance(schema, Mapping):
        return {}
    metadata: FieldMetadata = {
        namespace: dict(schema[namespace])
        for namespace in ("anyschema", "x-anyschema")
        if isinstance(schema.get(namespace), Mapping)
    }
    if (description := schema.get("description")) is not None and (
        get_anyschema_value_by_key(metadata, key="description") is None
    ):
        set_anyschema_meta(metadata, key="description", value=description)
    return metadata


def union_branches(schema: JsonSchema) -> list[JsonSchema] | None:
    """Return the branches of `anyOf`, `oneOf`, a single-item `allOf` or a `type` list, else None.

    Each branch also gets the keywords next to the union, and its own keywords win on conflicts.
    """
    for keyword in _UNION_KEYWORDS:
        branches = schema.get(keyword)
        if isinstance(branches, list) and (keyword != "allOf" or len(branches) == 1):
            siblings = {key: value for key, value in schema.items() if key != keyword}
            return [{**siblings, **branch} for branch in branches]
    if isinstance(json_type := schema.get("type"), list):
        return [{**schema, "type": type_name} for type_name in json_type]
    return None


def allows_null(schema: object) -> bool:
    """Whether `schema` allows `null` at its top level, looking through `anyOf`/`oneOf`/`allOf` and `type` lists.

    Nested subschemas such as `items` do not count: they make the elements nullable, not the field.
    """
    if not isinstance(schema, Mapping):
        return False
    if schema.get("type") == "null":
        return True
    if (branches := union_branches(schema)) is not None:
        return any(allows_null(branch) for branch in branches)
    if "const" in schema:
        return schema["const"] is None
    return isinstance(values := schema.get("enum"), list) and None in values
