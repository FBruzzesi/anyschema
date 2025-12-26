from __future__ import annotations

from contextlib import nullcontext as does_not_raise
from enum import Enum
from typing import TYPE_CHECKING, Any

import narwhals as nw
import pytest
from marshmallow import Schema, fields

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers import ParserPipeline
from anyschema.parsers.marshmallow import MarshmallowTypeStep

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from anyschema.typing import FieldMetadata


class UserSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    email = fields.Email()
    is_active = fields.Boolean()


@pytest.fixture
def marshmallow_pipeline() -> ParserPipeline:
    """Create a parser pipeline with marshmallow support."""
    return ParserPipeline("auto")


# (fields.NaiveDateTime, nw.String()),
# (fields.AwareDateTime, nw.String()),


class Color(Enum):
    BLUE = "blue"
    RED = "red"
    GREEN = "green"


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (fields.String(), nw.String()),
        (fields.Str(), nw.String()),
        (fields.Email(), nw.String()),
        (fields.Url(), nw.String()),
        (fields.UUID(), nw.String()),
        (fields.Boolean(), nw.Boolean()),
        (fields.Bool(), nw.Boolean()),
        (fields.Decimal(), nw.Decimal()),
        (fields.Integer(), nw.Int64()),
        (fields.Int(), nw.Int64()),
        (fields.Float(), nw.Float64()),
        (fields.Number(), nw.Float64()),
        (fields.DateTime(), nw.Datetime()),
        (fields.Date(), nw.Date()),
        (fields.Time(), nw.Time()),
        (fields.TimeDelta(), nw.Duration()),
        (fields.List(fields.Int()), nw.List(nw.Int64())),
        (fields.Tuple([fields.Float(), fields.Float()]), nw.Array(nw.Float64, shape=2)),
        (fields.Tuple([fields.Tuple([fields.Float(), fields.Float()])]), nw.Array(nw.Float64, shape=(1, 2))),
        (fields.Enum(Color), nw.Enum(Color)),
        (
            fields.Nested(UserSchema),
            nw.Struct({"id": nw.Int64(), "name": nw.String(), "email": nw.String(), "is_active": nw.Boolean()}),
        ),
    ],
)
def test_marshmallow_supported_dtypes(
    marshmallow_pipeline: ParserPipeline, input_type: fields.Field[Any], expected: nw.dtypes.DType
) -> None:
    result = marshmallow_pipeline.parse(input_type=input_type, constraints=(), metadata={})
    assert result == expected


@pytest.mark.parametrize(
    "input_type",
    [
        fields.Dict(),
        fields.Raw(),
        fields.Method(serialize="get_value"),
        fields.Function(serialize=lambda obj: obj),
        fields.Constant(constant=42),
        fields.IP(),
        fields.IPv4(),
        fields.IPv6(),
        fields.IPInterface(),
        fields.IPv4Interface(),
        fields.IPv6Interface(),
        fields.Mapping(),
    ],
)
def test_marshmallow_unsupported_dtypes(input_type: fields.Field[Any]) -> None:
    result = MarshmallowTypeStep().parse(input_type=input_type, constraints=(), metadata={})
    assert result is None


@pytest.mark.parametrize(
    ("input_type", "metadata", "context"),
    [
        (fields.AwareDateTime(), {"time_zone": "UTC", "time_unit": "ms"}, does_not_raise()),
        (fields.AwareDateTime(), {"time_unit": "ms"}, pytest.raises(UnsupportedDTypeError)),
        (fields.NaiveDateTime(), {"time_zone": "UTC", "time_unit": "ms"}, pytest.raises(UnsupportedDTypeError)),
        (fields.NaiveDateTime(), {"time_unit": "ms"}, does_not_raise()),
    ],
)
def test_marshmallow_datetime_dtypes(
    input_type: fields.Field[Any], metadata: FieldMetadata, context: AbstractContextManager[Any]
) -> None:
    with context:
        result = MarshmallowTypeStep().parse(input_type=input_type, constraints=(), metadata={"anyschema": metadata})
        assert isinstance(result, nw.Datetime)
