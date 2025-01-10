from __future__ import annotations

from typing import Final
import narwhals as nw
from narwhals.dtypes import DType
from pydantic.fields import FieldInfo
from annotated_types import Gt, Ge, Interval

INT_RANGES: Final[dict[DType, tuple[int, int]]] = {
    nw.Int8(): (-128, 127),
    nw.UInt8(): (0, 255),
    nw.Int16(): (-32768, 32767),
    nw.UInt16(): (0, 65535),
    nw.Int32(): (-2147483648, 2147483647),
    nw.UInt32(): (0, 4294967295),
    nw.Int64(): (-9223372036854775808, 9223372036854775807),
    nw.UInt64(): (0, 18446744073709551615),
}

_MIN_INT: Final[int] = -9_223_372_036_854_775_808
_MAX_INT: Final[int] = 18_446_744_073_709_551_615


def field_to_nw_type(field_info: FieldInfo) -> DType:
    """Parse Pydantic FieldInfo into narwhals dtype."""
    _type, _metadata = field_info.annotation, field_info.metadata
    if _type is int:
        return _parse_integer_metadata(_metadata)


def _parse_integer_metadata(metadata: list) -> DType:
    match metadata:
        case []:
            return nw.Int64()
        case [_, Interval(gt=gt, ge=ge, lt=lt, le=le), _]:
            lower_bound = max(gt or _MIN_INT, ge or _MIN_INT)
            upper_bound = min(lt or _MAX_INT, le or _MAX_INT)

            for dtype, (min_val, max_val) in INT_RANGES.items():
                if lower_bound > min_val and upper_bound < max_val:
                    return dtype
            return nw.Int64()
        case [Gt(gt=value)] | [Ge(ge=value)]:
            return nw.UInt64() if value >= 0 else nw.Int64()

        case _:
            msg = "Reached path that was though unreachable! Please raise an issue"
            raise AssertionError(msg)
