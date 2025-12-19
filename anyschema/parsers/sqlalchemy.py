from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw
from sqlalchemy import types as sqltypes

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType

__all__ = ("SQLAlchemyTypeStep",)

STRING_TYPES = (
    sqltypes.String,
    sqltypes.Text,
    sqltypes.Unicode,
    sqltypes.UnicodeText,
    sqltypes.JSON,  # In python and dataframes this is probably the best we can do for JSON
    sqltypes.Uuid,  # In python and dataframes this is probably the best we can do for UUID
)
BINARY_TYPES = (
    sqltypes._Binary,  # noqa: SLF001  # All binary dtypes inherit from this one
    sqltypes.LargeBinary,
    sqltypes.BINARY,
    sqltypes.VARBINARY,
    sqltypes.BLOB,
)


class SQLAlchemyTypeStep(ParserStep):
    """Parser for SQLAlchemy-specific types.

    Handles:

    - SQLAlchemy column types (Integer, String, DateTime, etc.)
    - SQLAlchemy relationship types
    - SQLAlchemy custom types

    Warning:
        It requires [sqlalchemy](https://www.sqlalchemy.org/) to be installed.
    """

    def parse(  # noqa: C901, PLR0912
        self,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> DType | None:
        """Parse SQLAlchemy-specific types into Narwhals dtypes.

        Arguments:
            input_type: The type to parse.
            constraints: Constraints associated with the type.
            metadata: Custom metadata dictionary.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        if not isinstance(input_type, sqltypes.TypeEngine):
            return None

        # NOTE: The order is quite important. In fact:
        #   * issubclass(Enum(...), String) -> True
        #   * issubclass(SmallInteger(), Integer) -> True
        #   * issubclass(Double(), Float) -> True
        if isinstance(input_type, sqltypes.Enum):
            categories = input_type.enum_class if input_type.enum_class is not None else input_type.enums
            return nw.Enum(categories)
        if isinstance(input_type, STRING_TYPES):
            return nw.String()
        if isinstance(input_type, sqltypes.Boolean):
            return nw.Boolean()
        if isinstance(input_type, sqltypes.SmallInteger):
            return nw.Int16()
        if isinstance(input_type, sqltypes.BigInteger):
            return nw.Int64()
        if isinstance(input_type, sqltypes.Integer):
            return nw.Int32()
        if isinstance(input_type, sqltypes.Double):
            return nw.Float64()
        if isinstance(input_type, (sqltypes.Float, sqltypes.REAL)):
            return nw.Float32()
        if isinstance(input_type, sqltypes.DECIMAL):
            return nw.Decimal()
        if isinstance(input_type, sqltypes.Numeric):
            # Safest option?
            return nw.Float64()
        if isinstance(input_type, sqltypes.Date):
            return nw.Date()
        if isinstance(input_type, sqltypes.DateTime):
            is_tz_aware, time_zone = input_type.timezone, metadata.get("anyschema/time_zone")
            if is_tz_aware and (time_zone is None):
                msg = (
                    "SQLAlchemy `DateTime(timezone=True)` does not specify a fixed timezone.\n\n"
                    "Hint: You can specify a timezone via `Column(..., info={'anyschema/time_zone': 'UTC'}` "
                    "or `mapped_column(..., info={'anyschema/time_zone': 'UTC'}`."
                )
                raise UnsupportedDTypeError(msg)
            if (not is_tz_aware) and (time_zone is not None):
                msg = f"SQLAlchemy `DateTime(timezone=False)` should not specify a fixed timezone, found {time_zone}"
                raise UnsupportedDTypeError(msg)
            return nw.Datetime(time_unit=metadata.get("anyschema/time_unit", "us"), time_zone=time_zone)
        if isinstance(input_type, sqltypes.Time):
            return nw.Time()
        if isinstance(input_type, sqltypes.Interval):
            return nw.Duration()
        if isinstance(input_type, BINARY_TYPES):
            return nw.Binary()
        if isinstance(input_type, sqltypes.ARRAY):
            # ARRAY.item_type is a TypeEngine instance, which is also a valid FieldType
            # SQLAlchemy's type stubs don't provide full generic parameter information for item_type
            inner_type = self.pipeline.parse(
                input_type.item_type, constraints=constraints, metadata=metadata, strict=True
            )
            if input_type.dimensions is None:
                return nw.List(inner=inner_type)
            else:
                return nw.Array(inner=inner_type, shape=input_type.dimensions)

        return None
