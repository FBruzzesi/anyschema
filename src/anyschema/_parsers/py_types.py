from __future__ import annotations

import enum
from collections.abc import Iterable, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from inspect import isclass
from typing import TYPE_CHECKING, TypeAlias, get_args, get_origin

import narwhals as nw

from anyschema._utils import unwrap_optional
from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    PythonDataType: TypeAlias = type[object]


def parse_py_type_into_nw_dtype(input_type: type[object]) -> DType | None:  # noqa: C901, PLR0911, PLR0912
    """Convert Python data type to Narwhals data type.

    Adapted from https://github.com/pola-rs/polars/blob/d95e343e04d47bcbeafc815a2d9855aa5099f1bb/py-polars/polars/datatypes/_parse.py#L72
    """
    input_type, _ = unwrap_optional(input_type)
    if input_type is int:
        return nw.Int64()
    if input_type is float:
        return nw.Float64()
    if input_type is str:
        return nw.String()
    if input_type is bool:
        return nw.Boolean()
    if isinstance(input_type, type) and issubclass(input_type, datetime):
        return nw.Datetime("us")
    if isinstance(input_type, type) and issubclass(input_type, date):
        return nw.Date()
    if input_type is timedelta:
        return nw.Duration()
    if input_type is time:
        return nw.Time()
    if input_type is Decimal:
        return nw.Decimal()
    if input_type is bytes:
        return nw.Binary()
    if input_type is object:
        return nw.Object()
    if isclass(input_type) and issubclass(input_type, enum.Enum):
        return nw.Enum(input_type)

    # Handle generic types (list, tuple, etc.)
    origin, args = get_origin(input_type), get_args(input_type)

    if (not args) and (origin in (list, tuple, Sequence, Iterable)):
        return nw.List(nw.Object())

    if not args or origin is None:
        return None

    inner_type, _ = unwrap_optional(args[0])
    inner_dtype = parse_py_type_into_nw_dtype(inner_type)

    if inner_dtype is None:
        return None

    if origin in (list, Sequence, Iterable):
        return nw.List(inner_dtype)

    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:  # noqa: PLR2004
            # tuple[T, ...] - variable length tuple
            return nw.List(inner_dtype)

        if len(set(args)) != 1:
            msg = f"Tuple with mixed types is not supported: {input_type}"
            raise UnsupportedDTypeError(msg)

        return nw.Array(inner_dtype, shape=len(args))

    return None
