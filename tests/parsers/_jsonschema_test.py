from __future__ import annotations

from typing import TYPE_CHECKING, Any

import narwhals as nw
import pytest

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers import JsonSchemaStep, ParserPipeline, ParserStep, PyTypeStep
from tests.conftest import json_object_schema

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


@pytest.fixture
def pipeline() -> ParserPipeline:
    # Deliberately without `AnnotatedTypesStep`: integer bounds must not depend on `annotated_types`.
    return ParserPipeline([JsonSchemaStep(), PyTypeStep()])


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"type": "string"}, nw.String()),
        ({"type": "string", "format": "uuid"}, nw.String()),  # unknown format: plain string
        ({"type": "string", "format": "date-time"}, nw.Datetime("us")),
        ({"type": "string", "format": "date"}, nw.Date()),
        ({"type": "string", "format": "time"}, nw.Time()),
        ({"type": "string", "format": "duration"}, nw.Duration()),
        ({"type": "string", "format": "binary"}, nw.Binary()),
        ({"type": "integer"}, nw.Int64()),
        ({"type": "number"}, nw.Float64()),
        ({"type": "boolean"}, nw.Boolean()),
        ({}, nw.Object()),
        ({"title": "Anything"}, nw.Object()),
        ({"type": "null"}, nw.Object()),
        ({"type": "array"}, nw.List(nw.Object())),
        ({"type": "array", "items": {"type": "integer"}}, nw.List(nw.Int64())),
        ({"type": "array", "prefixItems": [{"type": "number"}] * 3}, nw.Array(nw.Float64(), shape=3)),
        ({"type": "object"}, nw.Struct([])),
        ({"type": "object", "additionalProperties": {"type": "integer"}}, nw.Struct([])),
        (
            json_object_schema({"a": {"type": "integer"}, "b": json_object_schema({"c": {"type": "string"}})}),
            nw.Struct([nw.Field("a", nw.Int64()), nw.Field("b", nw.Struct([nw.Field("c", nw.String())]))]),
        ),
        ({"properties": {"a": {"type": "boolean"}}}, nw.Struct([nw.Field("a", nw.Boolean())])),  # implicit object
        ({"allOf": [{"type": "integer"}]}, nw.Int64()),
        ({"anyOf": [{"type": "number"}, {"type": "string"}]}, nw.Decimal()),  # Pydantic `Decimal`
    ],
)
def test_jsonschema_step_types(pipeline: ParserPipeline, schema: dict[str, Any], expected: DType) -> None:
    assert pipeline.parse(schema, (), {}) == expected


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"minimum": 0, "maximum": 255}, nw.UInt8()),
        ({"exclusiveMinimum": 0}, nw.UInt64()),
        ({"minimum": 0}, nw.UInt64()),
        ({"minimum": -128, "maximum": 127}, nw.Int8()),
        ({"exclusiveMinimum": -129, "exclusiveMaximum": 128}, nw.Int8()),
        ({"maximum": 10}, nw.Int64()),
        ({"minimum": 0.5, "maximum": 255.9}, nw.UInt8()),  # fractional bounds are rounded inward
        ({"minimum": -0.5, "maximum": 255}, nw.UInt8()),
        ({"minimum": 0, "exclusiveMinimum": True, "maximum": 255}, nw.UInt8()),  # draft-4 boolean is ignored
    ],
)
def test_jsonschema_step_integer_bounds(pipeline: ParserPipeline, schema: dict[str, Any], expected: DType) -> None:
    assert pipeline.parse({"type": "integer", **schema}, (), {}) == expected


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"enum": ["a", "b"]}, nw.Enum(["a", "b"])),
        ({"const": "a"}, nw.Enum(["a"])),
        ({"enum": [1, 2]}, nw.Int64()),
        ({"enum": [1, 2.5]}, nw.Float64()),
        ({"enum": [True, False]}, nw.Boolean()),
        ({"enum": [1, "a"]}, nw.Object()),
        ({"enum": [[1], [2]]}, nw.Object()),
        ({"enum": [None]}, nw.Object()),
    ],
)
def test_jsonschema_step_enum_const(pipeline: ParserPipeline, schema: dict[str, Any], expected: DType) -> None:
    assert pipeline.parse(schema, (), {}) == expected


@pytest.mark.parametrize(
    "schema",
    [
        {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        {"oneOf": [{"type": "null"}, {"type": "integer"}]},
        {"type": ["integer", "null"]},
        {"enum": [1, None]},
    ],
)
def test_jsonschema_step_nullable(pipeline: ParserPipeline, schema: dict[str, Any]) -> None:
    metadata: FieldMetadata = {}
    assert pipeline.parse(schema, (), metadata) == nw.Int64()
    assert metadata == {"anyschema": {"nullable": True}}


def test_jsonschema_step_explicit_nullable_is_preserved(pipeline: ParserPipeline) -> None:
    metadata: FieldMetadata = {"anyschema": {"nullable": False}}
    pipeline.parse({"type": ["string", "null"]}, (), metadata)
    assert metadata == {"anyschema": {"nullable": False}}


def test_jsonschema_step_type_list_keeps_sibling_keywords(pipeline: ParserPipeline) -> None:
    assert pipeline.parse({"type": ["integer", "null"], "minimum": 0, "maximum": 255}, (), {}) == nw.UInt8()


def test_jsonschema_step_datetime_metadata(pipeline: ParserPipeline) -> None:
    metadata: FieldMetadata = {"anyschema": {"time_zone": "UTC", "time_unit": "ms"}}
    assert pipeline.parse({"type": "string", "format": "date-time"}, (), metadata) == nw.Datetime("ms", "UTC")


def test_jsonschema_step_nested_field_metadata(pipeline: ParserPipeline) -> None:
    schema = json_object_schema({"ts": {"type": "string", "format": "date-time", "anyschema": {"time_zone": "UTC"}}})
    assert pipeline.parse(schema, (), {}) == nw.Struct([nw.Field("ts", nw.Datetime("us", "UTC"))])


@pytest.mark.parametrize(
    ("schema", "match"),
    [
        ({"anyOf": [{"type": "integer"}, {"type": "string"}]}, "mixed types"),
        ({"anyOf": [{"type": "number"}, {"type": "string", "format": "date-time"}]}, "mixed types"),
        ({"type": ["integer", "string"]}, "mixed types"),
        ({"type": "array", "prefixItems": [{"type": "integer"}, {"type": "string"}]}, "Tuple with mixed types"),
        ({"type": "foo"}, "Unsupported JSON Schema type: 'foo'"),
    ],
)
def test_jsonschema_step_unsupported_raises(pipeline: ParserPipeline, schema: dict[str, Any], match: str) -> None:
    with pytest.raises(UnsupportedDTypeError, match=match):
        pipeline.parse(schema, (), {})


@pytest.mark.parametrize(
    "input_type",
    [
        int,
        str,
        list[int],
        None,
        True,
        {"a": 1},  # plain mapping, not a schema
        {"b": int},
        {"$ref": "#/$defs/Address"},  # unresolved reference
        {"allOf": [{"type": "integer"}, {"minimum": 0}]},
        {"not": {"type": "string"}},
    ],
)
def test_jsonschema_step_unrecognized_input_returns_none(input_type: Any) -> None:
    step = JsonSchemaStep()
    _ = ParserPipeline([step])
    assert step.parse(input_type, (), {}) is None


def test_jsonschema_step_custom_step_intercepts_nested_subschema() -> None:
    class UUIDStep(ParserStep):
        def parse(
            self,
            input_type: FieldType,
            constraints: FieldConstraints,  # noqa: ARG002
            metadata: FieldMetadata,  # noqa: ARG002
        ) -> DType | None:
            if isinstance(input_type, dict) and input_type.get("format") == "uuid":
                return nw.Binary()
            return None

    pipeline = ParserPipeline.from_auto(UUIDStep())
    schema = {"type": "array", "items": {"type": "string", "format": "uuid"}}
    assert pipeline.parse(schema, (), {}) == nw.List(nw.Binary())
