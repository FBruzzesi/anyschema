"""JSON Schema helpers shared by `jsonschema_adapter` and `JsonSchemaStep`.

The adapter inlines every `$ref`, so the step can convert each subschema without the root document.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from anyschema._metadata import get_anyschema_value_by_key, set_anyschema_meta
from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from anyschema.typing import FieldMetadata, JsonSchema

__all__ = ("extract_field_metadata", "resolve_refs")

_TYPE_ANNOTATIONS = frozenset({"title", "description"})
"""Keywords of a referenced definition that document the type itself, not the field referring to it."""


def resolve_refs(node: Any, root: JsonSchema, _ref_path: tuple[str, ...] = ()) -> Any:
    """Return a copy of `node` with every local `$ref` replaced by the subschema it points to.

    Keywords next to a `$ref` win over the referenced ones. The referenced `title` and `description` are dropped,
    so a model docstring does not become the description of every field using that model.

    Arguments:
        node: The (sub)schema to resolve.
        root: The document that `$ref` pointers are resolved against.
        _ref_path: The `$ref`s being expanded on the current path, to detect cycles.

    Raises:
        UnsupportedDTypeError: If a `$ref` is recursive, since it has no finite dtype.
        ValueError: If a `$ref` is not local (`#...`) or cannot be resolved.
    """
    if isinstance(node, Mapping):
        if isinstance(ref := node.get("$ref"), str):
            if ref in _ref_path:
                msg = f"Recursive JSON Schema reference is not supported: {ref!r}."
                raise UnsupportedDTypeError(msg)
            target = {key: value for key, value in _resolve_pointer(root, ref).items() if key not in _TYPE_ANNOTATIONS}
            siblings = {key: value for key, value in node.items() if key != "$ref"}
            return resolve_refs({**target, **siblings}, root, (*_ref_path, ref))
        return {key: resolve_refs(value, root, _ref_path) for key, value in node.items()}
    if isinstance(node, list):
        return [resolve_refs(value, root, _ref_path) for value in node]
    return node


def _resolve_pointer(root: JsonSchema, ref: str) -> JsonSchema:
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

    Copies the `anyschema`/`x-anyschema` namespaces and maps the `description` keyword to the anyschema
    description, unless a namespace already sets one. Boolean subschemas (`true`/`false`) carry no metadata.
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
