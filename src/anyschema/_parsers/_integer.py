from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Final

import narwhals as nw
from annotated_types import Ge
from annotated_types import Gt
from annotated_types import Interval

if TYPE_CHECKING:
    from narwhals.dtypes import DType

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
