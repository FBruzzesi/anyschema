from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, TypeAlias

import narwhals as nw
from marshmallow import fields
from typing_extensions import TypeIs

from anyschema._metadata import get_anyschema_value_by_key
from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType, MarshmallowSchemaType


__all__ = ("MarshmallowTypeStep",)


STRING_TYPES = (
    fields.String,
    fields.Str,
    fields.Email,  # In python and dataframes this is probably the best we can do for Emails
    fields.Url,  # In python and dataframes this is probably the best we can do for URLs
    fields.UUID,  # In python and dataframes this is probably the best we can do for UUID
)

SupportedMarshmallowType: TypeAlias = (
    fields.String
    | fields.Str
    | fields.Email
    | fields.Url
    | fields.UUID
    | fields.Boolean
    | fields.Bool
    | fields.Decimal
    | fields.Integer
    | fields.Int
    | fields.Float
    | fields.Number[int | float | Decimal]
    | fields.DateTime
    | fields.NaiveDateTime
    | fields.AwareDateTime
    | fields.Date
    | fields.Time
    | fields.TimeDelta
    | fields.List[Any]
    | fields.Tuple
    | fields.Nested
    | fields.Enum[Any]
)
_SUPPORTED_MARSHMALLOW_TYPES = (
    fields.String,
    fields.Str,
    fields.Email,
    fields.Url,
    fields.UUID,
    fields.Boolean,
    fields.Bool,
    fields.Decimal,
    fields.Integer,
    fields.Int,
    fields.Float,
    fields.Number,
    fields.DateTime,
    fields.NaiveDateTime,
    fields.AwareDateTime,
    fields.Date,
    fields.Time,
    fields.TimeDelta,
    fields.List,
    fields.Tuple,
    fields.Nested,
    fields.Enum,
)


def _is_supported_marshmallow_type(obj: object) -> TypeIs[SupportedMarshmallowType]:
    return isinstance(obj, _SUPPORTED_MARSHMALLOW_TYPES)


class MarshmallowTypeStep(ParserStep):
    """Parser for Marshmallow-specific field types.

    Handles:

    - Marshmallow field types (String, Integer, Float, Boolean, etc.)
    - Marshmallow nested schemas (Nested, Pluck)
    - Marshmallow date/time fields (DateTime, Date, Time, TimeDelta)
    - Marshmallow collection fields (List, Dict, Tuple)

    Warning:
        It requires [marshmallow](https://marshmallow.readthedocs.io/) to be installed.
    """

    def parse(  # noqa: C901, PLR0912
        self,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> DType | None:
        """Parse Marshmallow field types into Narwhals dtypes.

        Arguments:
            input_type: The type to parse (marshmallow field instance).
            constraints: Constraints associated with the type.
            metadata: Custom metadata dictionary.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        if not isinstance(input_type, fields.Field):  # Keep this as a fast path!
            return None

        if not _is_supported_marshmallow_type(input_type):
            return None

        if isinstance(input_type, STRING_TYPES):
            return nw.String()

        if isinstance(input_type, (fields.Boolean, fields.Bool)):
            return nw.Boolean()

        if isinstance(input_type, fields.Decimal):
            return nw.Decimal()

        if isinstance(input_type, (fields.Integer, fields.Int)):
            return nw.Int64()

        if isinstance(input_type, (fields.Float, fields.Number)):
            return nw.Float64()

        if isinstance(input_type, fields.AwareDateTime):  # pyright: ignore[reportArgumentType]
            if (
                time_zone := (input_type.default_timezone or get_anyschema_value_by_key(metadata, key="time_zone"))
            ) is None:
                msg = (
                    "marwshmallow AwareDateTime does not specify a fixed timezone.\n\n"
                    "Hint: You can specify a timezone via "
                    "`marshmallow.fields.AwareDateTime(..., default_timezone=<time_zone>)` or "
                    "`marshmallow.fields.AwareDateTime(..., metadata={'anyschema': {'time_zone': <time_zone>}})`"
                )
                raise UnsupportedDTypeError(msg)

            return nw.Datetime(
                time_unit=get_anyschema_value_by_key(metadata, key="time_unit", default="us"), time_zone=str(time_zone)
            )

        if isinstance(input_type, fields.NaiveDateTime):  # pyright: ignore[reportArgumentType]
            if (
                time_zone := (input_type.timezone or get_anyschema_value_by_key(metadata, key="time_zone"))
            ) is not None:
                msg = f"marwshmallow NaiveDateTime should not not specify a timezone, found {time_zone}."
                raise UnsupportedDTypeError(msg)

            return nw.Datetime(
                time_unit=get_anyschema_value_by_key(metadata, key="time_unit", default="us"), time_zone=None
            )

        if isinstance(input_type, fields.DateTime):
            time_zone = get_anyschema_value_by_key(metadata, key="time_zone")
            time_unit = get_anyschema_value_by_key(metadata, key="time_unit", default="us")
            return nw.Datetime(time_unit=time_unit, time_zone=time_zone)

        if isinstance(input_type, fields.Date):
            return nw.Date()

        if isinstance(input_type, fields.Time):
            return nw.Time()

        if isinstance(input_type, fields.TimeDelta):
            time_unit = get_anyschema_value_by_key(metadata, key="time_unit", default="us")
            return nw.Duration(time_unit)

        if isinstance(input_type, fields.List):
            inner_dtype = self.pipeline.parse(input_type.inner, constraints=constraints, metadata=metadata, strict=True)
            return nw.List(inner_dtype)

        if isinstance(input_type, fields.Tuple):
            inner_types = tuple(
                self.pipeline.parse(field, constraints=constraints, metadata=metadata, strict=True)
                for field in input_type.tuple_fields
            )

            if len(set(inner_types)) > 1:
                msg = f"Tuple with mixed types is not supported: {input_type}"
                raise UnsupportedDTypeError(msg)

            shape = len(inner_types)
            return nw.Array(inner_types[0], shape=shape)

        if isinstance(input_type, fields.Enum):
            return nw.Enum(input_type.enum)  # ty: ignore[invalid-argument-type]

        # Nested schema
        nested_schema = input_type.schema
        return self._parse_nested_schema(type(nested_schema))

    def _parse_nested_schema(self, schema: MarshmallowSchemaType) -> DType:
        """Parse a nested Marshmallow schema into a Struct type.

        Arguments:
            schema: The Marshmallow Schema class.

        Returns:
            A Narwhals Struct dtype.
        """
        from anyschema.adapters import marshmallow_adapter

        return nw.Struct(
            [
                nw.Field(
                    name=field_name,
                    dtype=self.pipeline.parse(field_info, field_constraints, field_metadata, strict=True),
                )
                for field_name, field_info, field_constraints, field_metadata in marshmallow_adapter(schema)
            ]
        )
