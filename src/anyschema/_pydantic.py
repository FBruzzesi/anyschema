from __future__ import annotations

from datetime import date
from datetime import datetime
from types import NoneType
from types import UnionType
from typing import TYPE_CHECKING
from typing import Any
from typing import Final
from typing import GenericAlias
from typing import _GenericAlias

import narwhals as nw
from annotated_types import Ge
from annotated_types import Gt
from annotated_types import Interval
from narwhals.schema import Schema
from pydantic import AwareDatetime
from pydantic import FutureDate
from pydantic import FutureDatetime
from pydantic import NaiveDatetime
from pydantic import PastDate
from pydantic import PastDatetime

from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from narwhals.dtypes import DType
    from pydantic import BaseModel
    from pydantic.fields import FieldInfo


INT_RANGES: Final[dict[DType, tuple[int, int]]] = {
    nw.UInt8(): (0, 255),
    nw.UInt16(): (0, 65535),
    nw.UInt32(): (0, 4294967295),
    nw.UInt64(): (0, 18446744073709551615),
    nw.Int8(): (-128, 127),
    nw.Int16(): (-32768, 32767),
    nw.Int32(): (-2147483648, 2147483647),
    nw.Int64(): (-9223372036854775808, 9223372036854775807),
}

_MIN_INT: Final[int] = -9_223_372_036_854_775_808
_MAX_INT: Final[int] = 18_446_744_073_709_551_615


def model_to_nw_schema(model: BaseModel) -> Schema:
    """Converts Pydantic model to Narwhals Schema."""
    return Schema({field_name: field_to_nw_type(field_info) for field_name, field_info in model.model_fields.items()})


def field_to_nw_type(field_info: FieldInfo) -> DType:
    """Parse Pydantic FieldInfo into Narwhals dtype."""
    _type, _metadata = field_to_type_and_meta(field_info=field_info)

    if _type is int:
        # Includes:
        # - python int
        # - pydantic conint
        # - pydantic NegativeInt, NonNegativeInt, NonPositiveInt, PositiveInt
        return parse_integer_metadata(_metadata)

    if _type is float:
        # Includes:
        # - python float
        # - pydantic confloat
        # - pydantic FiniteFloat, NegativeFloat, NonNegativeFloat, NonPositiveFloat, PositiveFloat

        # There is no way of differentiating between Float32 and Float64 in pydantic,
        # therefore no matter what the metadata are, we always return Float64
        return nw.Float64()

    if _type is datetime:
        # Includes:
        # - python datetime
        # - pydantic AwareDatetime, NaiveDatetime, PastDatetime, FutureDatetime

        # As AwareDatetime does not pin-point a single timezone, and PastDatetime and FutureDatetime
        # accept both aware and naive datetimes, here we simply return nw.Datetime without timezone info.
        # However this means that we won't be able to convert it to a native timezone aware data type.
        return nw.Datetime()

    if _type is date:
        # Includes:
        # - python date
        # - pydantic condate
        # - pydantic PastDate, FutureDate
        return nw.Date()

    if _type is str:
        # Includes:
        # - python str
        # - pydantic constr, StrictStr
        # - pydantic Annotated[str, StringConstraints(...)]
        return nw.String()

    if _type is bool:
        # Includes:
        # - python bool
        # - pydantic StrictBool
        return nw.Boolean()

    raise NotImplementedError  # pragma: no cover


def field_to_type_and_meta(field_info: FieldInfo) -> tuple[type, tuple[Any]]:
    annotation = field_info.annotation
    if (is_union_type := isinstance(annotation, UnionType)) or isinstance(annotation, _GenericAlias | GenericAlias):
        if is_union_type and len(annotation.__args__) != 2:  # noqa: PLR2004
            msg = "Unsupported union with more than 2 types."
            raise NotImplementedError(msg)

        _field0, _field1 = annotation.__args__
        _field = _field1 if _field0 is NoneType else _field0
        _metadata = getattr(_field, "__metadata__", ())
        _type = getattr(_field, "__args__", (_field,))[0]

    else:
        _type = annotation
        _metadata = tuple(field_info.metadata)

    if _type is AwareDatetime:
        msg = "pydantic AwareDatetime does not specify a fixed timezone."
        raise UnsupportedDTypeError(msg)

    if _type in {AwareDatetime, NaiveDatetime, PastDatetime, FutureDatetime}:
        return datetime, ()

    if _type in {PastDate, FutureDate}:
        return date, ()

    return _type, _metadata


def parse_integer_metadata(metadata: list) -> DType:
    match metadata:
        # pydantic conint(...) case: generates metadata of the form [strict, Interval, multiple_of]
        case (_, Interval(gt=gt, ge=ge, lt=lt, le=le), _):
            lower_bound = max((gt + 1 if gt is not None else _MIN_INT), (ge if ge is not None else _MIN_INT))
            upper_bound = min((lt - 1 if lt is not None else _MAX_INT), (le if le is not None else _MAX_INT))

            for dtype, (min_val, max_val) in INT_RANGES.items():
                # As INT_RANGES is sorted by min_value first, and max_value second,
                # its guaranteed to fall within the smallest possible range.
                if lower_bound >= min_val and upper_bound <= max_val:
                    return dtype

            return nw.Int64()

        # pydantic NonNegativeInt & PositiveInt cases
        case (Gt(gt=value),) | (Ge(ge=value),):
            return nw.UInt64() if value >= 0 else nw.Int64()

        # All other cases: pure python int and pydantic remaining integer types
        case _:
            return nw.Int64()


__all__ = ("field_to_nw_type", "model_to_nw_schema")
