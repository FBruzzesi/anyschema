"""Conversion helpers from JSON Schema (objects) to anyschema field specifications.

The public entry point is [`jsonschema_adapter`][anyschema.adapters.jsonschema_adapter], which is a thin
wrapper around [`iter_field_specs`][anyschema._jsonschema.iter_field_specs] defined here.

The strategy is deliberately simple: rather than mapping JSON Schema constructs directly to Narwhals dtypes,
we translate each property into the equivalent Python type (e.g. `"integer"` to `int`, an object to a
dynamically created `TypedDict`, an array to `list[...]`) and let the regular
[`ParserPipeline`][anyschema.parsers.ParserPipeline] do the heavy lifting. This reuses all existing parsing
logic (nested structs, lists, optionals, integer-constraint refinement) for free.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any, Literal, Optional, Union, cast

from typing_extensions import TypedDict, TypeIs

from anyschema._dependencies import ANNOTATED_TYPES_AVAILABLE, is_jsonschema
from anyschema._metadata import get_anyschema_value_by_key, set_anyschema_meta
from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from anyschema.typing import FieldConstraints, FieldSpecIterable, JsonSchema

__all__ = ("iter_field_specs", "parse_schema")

# The type constructs below are built dynamically from runtime data, so we route them through `Any`-typed
# aliases. This keeps the (otherwise statically-special-cased) `Literal`/`Union`/`Optional`/`list` subscripts
# opaque to the type checkers, which cannot reason about non-literal arguments anyway.
_Literal: Any = Literal
_Union: Any = Union
_Optional: Any = Optional
_List: Any = list
_TypedDict: Any = TypedDict

_FORMAT_TO_TYPE: dict[str, type] = {
    "date-time": datetime,
    "date": date,
    "time": time,
    "duration": timedelta,
    "binary": bytes,
}
"""JSON Schema string `format` values mapped to the equivalent Python type."""


def parse_schema(spec: JsonSchema) -> Mapping[str, Any]:
    """Coerce and validate the input into a JSON Schema object mapping.

    Arguments:
        spec: A JSON Schema, either as a parsed mapping or as a raw `str`/`bytes` JSON document.

    Returns:
        The schema as a mapping.

    Raises:
        ValueError: If the input is not (or does not decode to) a JSON object with `"type": "object"` and
            a `"properties"` mapping.
    """
    schema = json.loads(spec) if isinstance(spec, (str, bytes, bytearray)) else spec

    if not is_jsonschema(schema):
        msg = "Expected a JSON Schema object with `'type': 'object'` and a `'properties'` mapping."
        raise ValueError(msg)

    return cast("Mapping[str, Any]", schema)


def iter_field_specs(schema: Mapping[str, Any]) -> FieldSpecIterable:
    """Yield field specifications for each property of a JSON Schema object.

    Arguments:
        schema: A validated JSON Schema object (see [`parse_schema`][anyschema._jsonschema.parse_schema]).

    Yields:
        Tuples of `(field_name, field_type, constraints, metadata)`.

    Notes:
        The `anyschema` / `x-anyschema` metadata namespaces (e.g. embedded by `pydantic`'s `json_schema_extra`)
        are propagated, so field-level hints such as `time_zone`, `time_unit` or an explicit `dtype` survive a
        round-trip. The top-level `description` keyword is mapped to the `anyschema` description.
    """
    defs = {**schema.get("$defs", {}), **schema.get("definitions", {})}
    for name, prop_schema in schema["properties"].items():
        field_type, constraints = _build_field_type(prop_schema, defs, name, frozenset())

        metadata: dict[str, Any] = {
            ns: dict(prop_schema[ns]) for ns in ("anyschema", "x-anyschema") if isinstance(prop_schema.get(ns), Mapping)
        }
        if (description := prop_schema.get("description")) is not None and (
            get_anyschema_value_by_key(metadata, key="description") is None
        ):
            set_anyschema_meta(metadata, key="description", value=description)

        yield name, field_type, constraints, metadata


def _build_field_type(
    schema: Mapping[str, Any], defs: Mapping[str, Any], name_hint: str, seen: frozenset[str]
) -> tuple[Any, FieldConstraints]:
    """Convert a single (possibly nullable/union) property schema into a Python type.

    Nullability is driven solely by the presence of the `null` type (via an `anyOf`/`oneOf` branch or a
    `type` array containing `"null"`); the schema-level `required` array is intentionally not consulted.

    Arguments:
        schema: The property subschema.
        defs: Mapping of definition name to subschema, used to resolve `$ref`.
        name_hint: Hint used to name dynamically created `TypedDict`s.
        seen: Set of `$ref` names already being expanded, used to detect cyclic references.

    Returns:
        A tuple of `(python_type, constraints)`. The type is wrapped in `Optional[...]` when null is allowed.
    """
    branches, has_null = _split_branches(schema)

    if len(branches) == 1:
        base, constraints = _base_type(branches[0], defs, name_hint, seen)
    elif not branches:  # only `null`, or an empty schema
        base, constraints = object, ()
    else:  # genuine multi-type union: defer to the pipeline (which rejects truly mixed unions)
        base = _Union[tuple(_base_type(b, defs, name_hint, seen)[0] for b in branches)]
        constraints = ()

    if has_null:
        base = _Optional[base]

    return base, constraints


def _base_type(  # noqa: C901
    schema: Mapping[str, Any], defs: Mapping[str, Any], name_hint: str, seen: frozenset[str]
) -> tuple[Any, FieldConstraints]:
    """Convert a single, non-nullable subschema into a Python type.

    Arguments:
        schema: The subschema to convert (must not be an `anyOf`/`oneOf`/null union).
        defs: Mapping of definition name to subschema, used to resolve `$ref`.
        name_hint: Hint used to name dynamically created `TypedDict`s.
        seen: Set of `$ref` names already being expanded, used to detect cyclic references.

    Returns:
        A tuple of `(python_type, constraints)`. Constraints are only populated for integers.
    """
    schema, seen = _resolve_ref(schema, defs, seen)

    if "const" in schema:
        return _Literal[schema["const"]], ()
    if "enum" in schema:
        return _Literal[tuple(schema["enum"])], ()

    json_type = schema.get("type")

    if json_type == "string":
        fmt = schema.get("format")
        return (_FORMAT_TO_TYPE.get(fmt, str) if isinstance(fmt, str) else str), ()
    if json_type == "integer":
        return int, _int_constraints(schema)
    if json_type == "number":
        return float, ()
    if json_type == "boolean":
        return bool, ()
    if json_type == "array":
        items = schema.get("items")
        if isinstance(items, Mapping):
            inner, _ = _build_field_type(items, defs, f"{name_hint}_item", seen)
            return _List[inner], ()
        return list, ()
    if json_type == "object":
        if isinstance(schema.get("properties"), Mapping):
            return _object_to_typed_dict(schema, defs, name_hint, seen), ()
        return dict, ()

    # No (or unsupported) `type`: fall back to an opaque object.
    return object, ()


def _object_to_typed_dict(
    schema: Mapping[str, Any], defs: Mapping[str, Any], name_hint: str, seen: frozenset[str]
) -> Any:
    """Build a dynamic `TypedDict` from a JSON Schema object so it parses into a Narwhals `Struct`.

    Arguments:
        schema: An object subschema with a `properties` mapping.
        defs: Mapping of definition name to subschema, used to resolve `$ref`.
        name_hint: Hint used to name the created `TypedDict`.
        seen: Set of `$ref` names already being expanded, used to detect cyclic references.

    Returns:
        A dynamically created `TypedDict` class.
    """
    fields = {
        key: _build_field_type(sub, defs, f"{name_hint}_{key}", seen)[0] for key, sub in schema["properties"].items()
    }
    name = schema.get("title") or name_hint
    return _TypedDict(name, fields)


def _resolve_ref(
    schema: Mapping[str, Any], defs: Mapping[str, Any], seen: frozenset[str]
) -> tuple[Mapping[str, Any], frozenset[str]]:
    """Resolve local `$ref` chains against `defs`, guarding against cycles.

    Arguments:
        schema: The subschema, possibly a `{"$ref": ...}` reference.
        defs: Mapping of definition name to subschema.
        seen: Set of `$ref` names already being expanded.

    Returns:
        A tuple of `(resolved_schema, updated_seen)`.

    Raises:
        UnsupportedDTypeError: If a cyclic (self-referential) reference is detected.
        ValueError: If a reference cannot be resolved against `defs`.
    """
    while "$ref" in schema:
        ref = schema["$ref"]
        name = ref.rsplit("/", 1)[-1]
        if name in seen:
            msg = f"Recursive/cyclic JSON Schema reference is not supported: {ref!r}."
            raise UnsupportedDTypeError(msg)
        if name not in defs:
            msg = f"Could not resolve JSON Schema reference: {ref!r}."
            raise ValueError(msg)
        seen = seen | {name}
        schema = defs[name]
    return schema, seen


def _split_branches(schema: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], bool]:
    """Split a subschema into its non-null branches and whether `null` is allowed.

    Handles `anyOf`/`oneOf` unions as well as a `type` given as a list (e.g. `["integer", "null"]`).

    Arguments:
        schema: The subschema to inspect.

    Returns:
        A tuple of `(non_null_branches, has_null)`.
    """
    for key in ("anyOf", "oneOf"):
        if key in schema:
            subs = schema[key]
            return [s for s in subs if not _is_null(s)], any(_is_null(s) for s in subs)

    if isinstance(json_type := schema.get("type"), list):
        rest = {k: v for k, v in schema.items() if k != "type"}
        branches: list[Mapping[str, Any]] = [{**rest, "type": t} for t in json_type if t != "null"]
        return branches, "null" in json_type

    if _is_null(schema):
        return [], True
    return [schema], False


def _is_null(schema: object) -> bool:
    """Return whether a subschema denotes the JSON `null` type."""
    return isinstance(schema, Mapping) and schema.get("type") == "null"


def _int_constraints(schema: Mapping[str, Any]) -> FieldConstraints:
    """Map JSON Schema numeric bounds to `annotated_types` constraints for integer dtype refinement.

    Returns an empty tuple when `annotated_types` is not installed (the pipeline would ignore the
    constraints anyway), so that JSON integers degrade gracefully to `Int64`.

    Arguments:
        schema: An integer subschema, possibly carrying `minimum`/`maximum`/`exclusiveMinimum`/`exclusiveMaximum`.

    Returns:
        A tuple of `annotated_types` constraint instances (e.g. `Gt(0)`).
    """
    if not ANNOTATED_TYPES_AVAILABLE:
        return ()

    from annotated_types import Ge, Gt, Le, Lt

    # `isinstance(..., bool)` guards against the legacy draft-4 boolean `exclusive*` form.
    constraints: list[Any] = []
    if _is_number(minimum := schema.get("minimum")):
        constraints.append(Ge(minimum))
    if _is_number(excl_min := schema.get("exclusiveMinimum")):
        constraints.append(Gt(excl_min))
    if _is_number(maximum := schema.get("maximum")):
        constraints.append(Le(maximum))
    if _is_number(excl_max := schema.get("exclusiveMaximum")):
        constraints.append(Lt(excl_max))
    return tuple(constraints)


def _is_number(value: object) -> TypeIs[float]:
    """Return whether a value is a real number (excluding the legacy draft-4 boolean `exclusive*` form)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)
