from __future__ import annotations

from typing import TYPE_CHECKING, Any

import narwhals as nw
from sqlalchemy import types as sqltypes

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

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

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        """Parse SQLAlchemy-specific types into Narwhals dtypes.

        Arguments:
            input_type: The SQLAlchemy type to parse.
            metadata: Optional metadata associated with the type (e.g., nullable).

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        if not isinstance(input_type, sqltypes.TypeEngine):
            return None

        return self._map_sqlalchemy_type(input_type, metadata)

    def _map_sqlalchemy_type(self, sql_type: sqltypes.TypeEngine, metadata: tuple = ()) -> DType | None:
        """Map a SQLAlchemy type to a Narwhals dtype.

        Arguments:
            sql_type: The SQLAlchemy type instance.
            metadata: Optional metadata (e.g., nullable).

        Returns:
            A Narwhals DType.
        """
        # NOTE: The order is quite important. In fact:
        #   * issubclass(SmallInteger, Integer) -> True
        #   * issubclass(Double(), Float) -> True
        if isinstance(sql_type, STRING_TYPES):
            return nw.String()
        if isinstance(sql_type, sqltypes.Boolean):
            return nw.Boolean()
        if isinstance(sql_type, sqltypes.SmallInteger):
            return nw.Int16()
        if isinstance(sql_type, sqltypes.BigInteger):
            return nw.Int64()
        if isinstance(sql_type, sqltypes.Integer):
            return nw.Int32()
        if isinstance(sql_type, sqltypes.Double):
            return nw.Float64()
        if isinstance(sql_type, (sqltypes.Float, sqltypes.REAL)):
            return nw.Float32()
        if isinstance(sql_type, sqltypes.DECIMAL):
            return nw.Decimal()
        if isinstance(sql_type, sqltypes.Numeric):
            # Safest option?
            return nw.Float64()
        if isinstance(sql_type, sqltypes.Date):
            return nw.Date()
        if isinstance(sql_type, sqltypes.DateTime):
            # Check for timezone awareness
            if hasattr(sql_type, "timezone") and sql_type.timezone:
                msg = "TODO: How can we extrapolate the timezone value?"
                raise NotImplementedError(msg)
            return nw.Datetime()
        if isinstance(sql_type, sqltypes.Time):
            return nw.Time()
        if isinstance(sql_type, sqltypes.Interval):
            return nw.Duration()
        if isinstance(sql_type, BINARY_TYPES):
            return nw.Binary()
        if isinstance(sql_type, sqltypes.Enum):
            categories = sql_type.enum_class if sql_type.enum_class is not None else sql_type.enums
            return nw.Enum(categories)

        if isinstance(sql_type, sqltypes.ARRAY):
            inner_type = self._map_sqlalchemy_type(sql_type.item_type, metadata=metadata)

            if inner_type is None:
                msg = (
                    f"Found unsupported inner type: {sql_type.item_type}.\n\n"
                    f"Please consider opening a feature request https://github.com/FBruzzesi/anyschema/issues"
                )
                raise UnsupportedDTypeError(msg)
            if sql_type.dimensions is None:
                return nw.List(inner=inner_type)
            else:
                return nw.Array(inner=inner_type, shape=sql_type.dimensions)

        return None
