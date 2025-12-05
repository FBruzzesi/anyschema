from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final, TypeAlias

import narwhals as nw
from annotated_types import Ge, Gt, Interval, Le, Lt

from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    LowerBound: TypeAlias = int
    UpperBound: TypeAlias = int
    Range: TypeAlias = tuple[LowerBound, UpperBound]


__all__ = ("AnnotatedTypesStep",)

UINT_RANGES: Final[dict[DType, Range]] = {
    nw.UInt8(): (0, 255),
    nw.UInt16(): (0, 65535),
    nw.UInt32(): (0, 4294967295),
    nw.UInt64(): (0, 18446744073709551615),
}
"""Unsigned integer ranges, both included.

The mapping is sorted by `UpperBound` ascending for smallest-fit selection.
"""

INT_RANGES: Final[dict[DType, Range]] = {
    nw.Int8(): (-128, 127),
    nw.Int16(): (-32768, 32767),
    nw.Int32(): (-2147483648, 2147483647),
    nw.Int64(): (-9223372036854775808, 9223372036854775807),
}
"""Signed integer ranges, both included.

The mapping is sorted by `UpperBound` ascending for smallest-fit selection
"""

MIN_INT: Final[int] = -9_223_372_036_854_775_808
MAX_INT: Final[int] = 18_446_744_073_709_551_615


class AnnotatedTypesStep(ParserStep):
    """Parser for types with `annotated_types` metadata.

    Handles:

    - Integer constraints (`Gt`, `Ge`, `Lt`, `Le`, `Interval`)
    - Type refinement based on metadata

    Warning:
        It requires [annotated-types](https://github.com/annotated-types/annotated-types) to be installed.
    """

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        """Parse types with annotated metadata into refined Narwhals dtypes.

        Arguments:
            input_type: The type to parse.
            metadata: Metadata associated with the type (e.g., constraints).

        Returns:
            A Narwhals DType if this parser can refine the type based on metadata, None otherwise.
        """
        if not metadata:
            return None

        # Check if it's a type/class and if it's int or a subclass of int (but not bool)
        # Note: bool is a subclass of int, but we don't want to apply integer constraints to booleans
        if isinstance(input_type, type) and issubclass(input_type, int) and not issubclass(input_type, bool):
            return self._parse_integer_metadata(metadata)

        # For other types, we don't refine based on metadata
        return None

    def _parse_integer_metadata(self, metadata: tuple[Any, ...]) -> DType:  # noqa: C901, PLR0912
        """Parse integer type constraints from metadata to determine the most appropriate integer dtype.

        This function examines annotated_types constraints (Gt, Ge, Lt, Le, Interval) to determine
        the smallest integer dtype that can accommodate the specified range.

        Arguments:
            metadata: Tuple of metadata objects, potentially containing annotated_types constraints.

        Returns:
            The most appropriate integer DType based on the constraints.
        """
        # Extract constraint values safely
        lower_bound, upper_bound = MIN_INT, MAX_INT

        for item in metadata:
            if isinstance(item, Interval):
                # Handle Interval constraint (e.g., from pydantic conint)
                if item.gt is not None:
                    lower_bound = max(lower_bound, int(self._extract_numeric_value(item.gt)) + 1)
                if item.ge is not None:
                    lower_bound = max(lower_bound, int(self._extract_numeric_value(item.ge)))
                if item.lt is not None:
                    upper_bound = min(upper_bound, int(self._extract_numeric_value(item.lt)) - 1)
                if item.le is not None:
                    upper_bound = min(upper_bound, int(self._extract_numeric_value(item.le)))

            elif isinstance(item, Gt):  #  It includes pydantic PositiveInt
                lower_bound = max(lower_bound, int(self._extract_numeric_value(item.gt)) + 1)

            elif isinstance(item, Ge):  #  It includes pydantic NonNegativeInt
                lower_bound = max(lower_bound, int(self._extract_numeric_value(item.ge)))

            elif isinstance(item, Lt):
                upper_bound = min(upper_bound, int(self._extract_numeric_value(item.lt)) - 1)

            elif isinstance(item, Le):
                upper_bound = min(upper_bound, int(self._extract_numeric_value(item.le)))

        # Choose between signed and unsigned based on lower_bound
        if lower_bound >= 0:
            # Range is non-negative, use unsigned integers (smaller memory footprint)
            for dtype, (_, _upper) in UINT_RANGES.items():
                if upper_bound <= _upper:
                    return dtype
            # If no unsigned type fits, use UInt64
            return nw.UInt64()
        else:
            # Range includes negative values, use signed integers
            for dtype, (_lower, _upper) in INT_RANGES.items():
                if lower_bound >= _lower and upper_bound <= _upper:
                    return dtype
            # If no signed type fits, use Int64
            return nw.Int64()

    @staticmethod
    def _extract_numeric_value(value: Any) -> int | float:
        """Safely extract a numeric value from a constraint value.

        This handles the Protocol types used by annotated_types (SupportsGt, SupportsGe, etc.)
        by converting them to int or float.

        Arguments:
            value: The value to extract, which may be a number or a Protocol type.

        Returns:
            The numeric value as int or float.

        Raises:
            TypeError: If the value cannot be converted to a number.
        """
        if value is None:
            msg = "Cannot extract numeric value from None"
            raise TypeError(msg)

        if isinstance(value, (int, float)):
            return value

        try:
            return int(value)
        except (TypeError, ValueError):
            try:
                return float(value)
            except (TypeError, ValueError) as e:
                msg = f"Cannot convert {type(value).__name__} to numeric value: {value}"
                raise TypeError(msg) from e
