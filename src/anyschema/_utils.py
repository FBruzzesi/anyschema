from typing import TYPE_CHECKING
from typing import Final

import narwhals as nw

if TYPE_CHECKING:
    from narwhals.dtypes import DType

__all__ = ("UINT_RANGES", "INT_RANGES", "MIN_INT", "MAX_INT")

UINT_RANGES: Final[dict[DType, tuple[int, int]]] = {
    nw.UInt8(): (0, 255),
    nw.UInt16(): (0, 65535),
    nw.UInt32(): (0, 4294967295),
    nw.UInt64(): (0, 18446744073709551615),
}
"""Unsigned integer ranges, both included.

Mapping is sorted by max_value ascending for smallest-fit selection
"""
 
INT_RANGES: Final[dict[DType, tuple[int, int]]] = {
    nw.Int8(): (-128, 127),
    nw.Int16(): (-32768, 32767),
    nw.Int32(): (-2147483648, 2147483647),
    nw.Int64(): (-9223372036854775808, 9223372036854775807),
}
"""Signed integer ranges, both included.

Mapping is sorted by max_value ascending for smallest-fit selection
"""

MIN_INT: Final[int] = -9_223_372_036_854_775_808
MAX_INT: Final[int] = 18_446_744_073_709_551_615
