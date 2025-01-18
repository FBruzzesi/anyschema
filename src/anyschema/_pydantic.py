from __future__ import annotations

from datetime import date
from datetime import datetime
from types import NoneType
from types import UnionType
from typing import TYPE_CHECKING
from typing import Any
from typing import Final
from typing import GenericAlias
from typing import Union
from typing import _GenericAlias
from narwhals.utils import isinstance_or_issubclass

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
from pydantic.fields import FieldInfo

from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from narwhals.dtypes import DType
    from pydantic import BaseModel
    


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
    return Schema(
        {field_name: pydantic_field_to_nw_type(field_info) for field_name, field_info in model.model_fields.items()}
    )


def pydantic_field_to_nw_type(field_info: FieldInfo) -> tuple[type, tuple[Any]]:  # noqa: C901, PLR0911, PLR0912
    annotation = field_info.annotation

    if isinstance(annotation, _GenericAlias | GenericAlias):
        _origin = annotation.__origin__
        _args = annotation.__args__

        if _origin is Union:
            _type, _metadata = parse_union(_args)
            return pydantic_field_to_nw_type(FieldInfo(annotation=_type, metadata=_metadata))

        elif _origin is list:
            # List(inner...)
            raise NotImplementedError

        elif _origin is dict or isinstance_or_issubclass(_origin, BaseModel):
            # Struct(fields...)
            raise NotImplementedError

        else:
            raise NotImplementedError

    elif isinstance(annotation, UnionType):
        _type, _metadata = parse_union(annotation.__args__)

    else:
        _type = annotation
        _metadata = tuple(field_info.metadata)

    if _type is AwareDatetime:
        # Pydantic AwareDatetime does not fix a single timezone, but any timezone would work.
        # This cannot be used in nw.Datetime, therefore we raise an exception
        # See https://github.com/pydantic/pydantic/issues/5829
        msg = "pydantic AwareDatetime does not specify a fixed timezone."
        raise UnsupportedDTypeError(msg)

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

    if _type in {datetime, NaiveDatetime, PastDatetime, FutureDatetime}:
        # Includes:
        # - python datetime
        # - pydantic AwareDatetime, NaiveDatetime, PastDatetime, FutureDatetime

        # PastDatetime and FutureDatetime accept both aware and naive datetimes, here we
        # simply return nw.Datetime without timezone info.
        # This means that we won't be able to convert it to a timezone aware data type.
        return nw.Datetime()

    if _type in {date, PastDate, FutureDate}:
        # Includes:
        # - python date
        # - pydantic condate
        # - pydantic PastDate, FutureDate
        return nw.Date()

    raise NotImplementedError  # pragma: no cover


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


def parse_union(union: UnionType) -> tuple[type, tuple[Any]]:
    if len(union) != 2:  # noqa: PLR2004
        msg = "Unsupported union with more than two types."
        raise NotImplementedError(msg)

    _field0, _field1 = union
    _field = _field1 if _field0 is NoneType else _field0
    _metadata = getattr(_field, "__metadata__", ())
    _type = getattr(_field, "__args__", (_field,))[0]

    return _type, _metadata


__all__ = ("model_to_nw_schema", "pydantic_field_to_nw_type")
