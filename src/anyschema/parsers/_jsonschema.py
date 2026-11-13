from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from math import ceil, floor
from typing import TYPE_CHECKING, Any, Final

import narwhals as nw
from typing_extensions import TypeIs

from anyschema._jsonschema import extract_field_metadata
from anyschema._metadata import get_anyschema_value_by_key, set_anyschema_meta
from anyschema._utils import INT64_MIN, UINT64_MAX, int_dtype_from_bounds
from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType, JsonSchema

__all__ = ("JsonSchemaStep",)

_PY_TYPE_BY_JSON_TYPE: Final[Mapping[str, type]] = {"string": str, "integer": int, "number": float, "boolean": bool}

_PY_TYPE_BY_STRING_FORMAT: Final[Mapping[str, type]] = {
    "date-time": datetime,
    "date": date,
    "time": time,
    "duration": timedelta,
    "binary": bytes,
}

_PY_TYPE_BY_ENUM_VALUE_TYPES: Final[Mapping[frozenset[type], type]] = {
    frozenset({bool}): bool,
    frozenset({int}): int,
    frozenset({float}): float,
    frozenset({int, float}): float,
}

_ANNOTATION_KEYWORDS: Final = frozenset(
    {"title", "description", "default", "examples", "deprecated", "readOnly", "writeOnly", "$comment"}
    | {"anyschema", "x-anyschema"}
)
"""Keywords that do not constrain a value: a schema made only of these accepts anything."""


class JsonSchemaStep(ParserStep):
    """Parser for [JSON Schema](https://json-schema.org/) subschemas, as yielded by
    [`jsonschema_adapter`][anyschema.adapters.jsonschema_adapter].

    - `object` becomes a `Struct` of its `properties`.
    - `array` becomes a `List` of its `items`, or an `Array` when `prefixItems` share one dtype (as emitted for
        `tuple[int, int]`).
    - `integer` bounds (`minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`) pick the smallest fitting
        integer dtype, e.g. `{"type": "integer", "exclusiveMinimum": 0}` becomes `UInt64`.
    - String `enum`/`const` become an `Enum`, other values the dtype of their scalar type.
    - A `null` branch in `anyOf`/`oneOf` or a `type` list marks the field nullable. `anyOf: [number, string]` becomes
        `Decimal`, matching what Pydantic emits for `Decimal` fields. Other unions with mixed types are rejected.
    - A schema without `type` or constraints, such as `{}` for `typing.Any`, becomes `Object`.
    - Other scalars are parsed as the equivalent Python type (e.g. `"format": "date-time"` as `datetime`), so
        metadata such as `time_zone` and `time_unit` applies as for any other spec.

    Mappings it does not recognize (e.g. an unresolved `$ref`) are left to the next step.

    Nested subschemas go through the pipeline, so a custom step placed before this one can intercept any of them,
    e.g. to map `{"type": "string", "format": "uuid"}` to a dedicated dtype.
    """

    def parse(  # noqa: C901
        self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata
    ) -> DType | None:
        """Parse a JSON Schema subschema into a Narwhals dtype.

        Arguments:
            input_type: The type to parse. Only mappings are handled.
            constraints: Constraints associated with the type, passed on to scalar types.
            metadata: Custom metadata dictionary. Marked nullable in place when the schema allows `null`.

        Returns:
            A Narwhals DType if `input_type` is a JSON Schema this step understands, None otherwise.
        """
        if not isinstance(input_type, Mapping):  # Keep this as a fast path!
            return None

        schema: JsonSchema = input_type
        if (branches := _union_branches(schema)) is not None:
            return self._parse_union(branches, constraints, metadata)
        if "const" in schema:
            return self._parse_enum([schema["const"]], metadata)
        if "enum" in schema:
            return self._parse_enum(schema["enum"], metadata)

        json_type = schema.get("type", "object" if "properties" in schema else None)
        if json_type is None:
            return nw.Object() if schema.keys() <= _ANNOTATION_KEYWORDS else None
        if json_type == "object":
            return nw.Struct(
                [
                    nw.Field(name, self.pipeline.parse(property_schema, (), extract_field_metadata(property_schema)))
                    for name, property_schema in schema.get("properties", {}).items()
                ]
            )
        if json_type == "array":
            return self._parse_array(schema, constraints, metadata)
        if json_type == "integer" and (bounds := _integer_bounds(schema)) is not None:
            return int_dtype_from_bounds(*bounds)
        if json_type == "string" and (py_type := _PY_TYPE_BY_STRING_FORMAT.get(str(schema.get("format")))):
            return self.pipeline.parse(py_type, constraints, metadata)
        if json_type in _PY_TYPE_BY_JSON_TYPE:
            return self.pipeline.parse(_PY_TYPE_BY_JSON_TYPE[json_type], constraints, metadata)

        msg = f"Unsupported JSON Schema type: {json_type!r}."
        raise UnsupportedDTypeError(msg)

    def _parse_union(
        self, branches: Sequence[JsonSchema], constraints: FieldConstraints, metadata: FieldMetadata
    ) -> DType:
        non_null_branches = [branch for branch in branches if branch.get("type") != "null"]
        if len(non_null_branches) < len(branches):
            _set_nullable(metadata)
        if not non_null_branches:
            return nw.Object()
        if len(non_null_branches) == 1:
            return self.pipeline.parse(non_null_branches[0], constraints, metadata)
        if _is_decimal_union(non_null_branches):
            return self.pipeline.parse(Decimal, constraints, metadata)
        msg = "Union with mixed types is not supported."
        raise UnsupportedDTypeError(msg)

    def _parse_enum(self, values: Sequence[Any], metadata: FieldMetadata) -> DType:
        non_null_values = [value for value in values if value is not None]
        if len(non_null_values) < len(values):
            _set_nullable(metadata)
        value_types = frozenset(type(value) for value in non_null_values)
        if value_types == frozenset({str}):
            return nw.Enum(non_null_values)
        # Narwhals `Enum` categories must be strings, so other values fall back to their scalar dtype.
        return self.pipeline.parse(_PY_TYPE_BY_ENUM_VALUE_TYPES.get(value_types, object), (), metadata)

    def _parse_array(self, schema: JsonSchema, constraints: FieldConstraints, metadata: FieldMetadata) -> DType:
        if prefix_items := schema.get("prefixItems"):
            item_dtypes = [self.pipeline.parse(item, constraints, metadata) for item in prefix_items]
            if any(dtype != item_dtypes[0] for dtype in item_dtypes):
                msg = f"Tuple with mixed types is not supported: {schema!r}"
                raise UnsupportedDTypeError(msg)
            return nw.Array(item_dtypes[0], shape=len(item_dtypes))
        if isinstance(items := schema.get("items"), Mapping):
            return nw.List(self.pipeline.parse(items, constraints, metadata))
        return nw.List(nw.Object())


def _union_branches(schema: JsonSchema) -> list[JsonSchema] | None:
    """Return the branches of `anyOf`, `oneOf`, a single-item `allOf` or a `type` list, else None."""
    for keyword in ("anyOf", "oneOf"):
        if isinstance(branches := schema.get(keyword), list):
            return branches
    if isinstance(all_of := schema.get("allOf"), list) and len(all_of) == 1:  # e.g. `{"allOf": [{"$ref": ...}]}`
        return all_of
    if isinstance(json_type := schema.get("type"), list):
        return [{**schema, "type": type_name} for type_name in json_type]
    if json_type == "null":
        return [schema]
    return None


def _is_decimal_union(branches: Sequence[JsonSchema]) -> bool:
    # shortcut: `float | str` emits the same `anyOf: [number, string]` and is read as Decimal too. Pydantic drops
    # `max_digits`/`decimal_places` from the schema, so the precision is the `Decimal` default either way.
    branch_types = [branch.get("type") for branch in branches]
    return (
        len(branch_types) == 2  # noqa: PLR2004
        and "number" in branch_types
        and "string" in branch_types
        and not any("format" in branch for branch in branches)
    )


def _integer_bounds(schema: JsonSchema) -> tuple[int, int] | None:
    """Return the inclusive `(lower, upper)` bounds of an integer schema, or None if it is unbounded."""
    lower, upper = INT64_MIN, UINT64_MAX
    if _is_number(value := schema.get("minimum")):
        lower = max(lower, ceil(value))
    if _is_number(value := schema.get("exclusiveMinimum")):  # The draft 4 boolean form is not a number.
        lower = max(lower, floor(value) + 1)
    if _is_number(value := schema.get("maximum")):
        upper = min(upper, floor(value))
    if _is_number(value := schema.get("exclusiveMaximum")):
        upper = min(upper, ceil(value) - 1)
    return None if (lower, upper) == (INT64_MIN, UINT64_MAX) else (lower, upper)


def _is_number(value: object) -> TypeIs[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _set_nullable(metadata: FieldMetadata) -> None:
    if get_anyschema_value_by_key(metadata, key="nullable") is None:
        set_anyschema_meta(metadata, key="nullable", value=True)
