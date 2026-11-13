"""JSON Schema helpers shared by `jsonschema_adapter` and `JsonSchemaStep`."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Final, TypeVar, overload

from anyschema._metadata import get_anyschema_value_by_key, set_anyschema_meta
from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from anyschema.typing import FieldMetadata, JsonSchema

__all__ = ("extract_field_metadata", "inline_refs")

_T = TypeVar("_T")

_SUBSCHEMA_KEYWORDS: Final = frozenset({"items", "prefixItems", "anyOf", "oneOf", "allOf"})
"""Keywords holding a subschema or a list of subschemas that `JsonSchemaStep` reads, besides `properties`.

Other keywords are copied as-is: `default`, `examples`, `const` and `enum` hold instance data, which may contain a
literal `"$ref"` key, and `additionalProperties` is not converted.
"""

_DEFINITION_DOC_KEYWORDS: Final = frozenset({"title", "description"})
"""Keywords of a referenced definition that describe the definition, not the field pointing to it."""


def inline_refs(schema: JsonSchema, root: JsonSchema, _expanding: tuple[str, ...] = ()) -> JsonSchema:
    """Return a copy of `schema` with every local `$ref` replaced by the definition it points to.

    Keywords next to a `$ref` override the referenced ones. The referenced `title` and `description` are dropped, so
    a model docstring does not become the description of every field of that model type.

    Arguments:
        schema: The (sub)schema to resolve.
        root: The document that `$ref` pointers are resolved against.
        _expanding: The `$ref`s being expanded on the current path, used to detect cycles.

    Raises:
        UnsupportedDTypeError: If a `$ref` is recursive, since it has no finite dtype.
        ValueError: If a `$ref` is not local (`#...`) or cannot be resolved.
    """
    if isinstance(ref := schema.get("$ref"), str):
        if ref in _expanding:
            msg = f"Recursive JSON Schema reference is not supported: {ref!r}."
            raise UnsupportedDTypeError(msg)
        definition = _resolve_json_pointer(root, ref)
        merged = {key: value for key, value in definition.items() if key not in _DEFINITION_DOC_KEYWORDS}
        merged.update((key, value) for key, value in schema.items() if key != "$ref")
        return inline_refs(merged, root, (*_expanding, ref))

    inlined = dict(schema)
    if isinstance(properties := schema.get("properties"), Mapping):
        inlined["properties"] = {name: _inline_refs_in(sub, root, _expanding) for name, sub in properties.items()}
    for keyword in _SUBSCHEMA_KEYWORDS & schema.keys():
        inlined[keyword] = _inline_refs_in(schema[keyword], root, _expanding)
    return inlined


@overload
def _inline_refs_in(value: JsonSchema, root: JsonSchema, expanding: tuple[str, ...]) -> JsonSchema: ...
@overload
def _inline_refs_in(value: list[Any], root: JsonSchema, expanding: tuple[str, ...]) -> list[Any]: ...
@overload
def _inline_refs_in(value: _T, root: JsonSchema, expanding: tuple[str, ...]) -> _T: ...
def _inline_refs_in(value: object, root: JsonSchema, expanding: tuple[str, ...]) -> object:
    """Inline refs in a subschema or a list of subschemas. Boolean subschemas are returned unchanged."""
    if isinstance(value, Mapping):
        return inline_refs(value, root, expanding)
    if isinstance(value, list):
        return [_inline_refs_in(item, root, expanding) for item in value]
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
