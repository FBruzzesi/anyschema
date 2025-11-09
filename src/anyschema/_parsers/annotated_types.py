from __future__ import annotations

from typing import TYPE_CHECKING, Any

import narwhals as nw
from annotated_types import Ge, Gt, Interval, Le, Lt, MultipleOf

from anyschema._utils import INT_RANGES, MAX_INT, MIN_INT, UINT_RANGES

if TYPE_CHECKING:
    from narwhals.dtypes import DType


def _extract_numeric_value(value: Any) -> int | float:  # noqa: ANN401
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


def parse_integer_constraints(metadata: tuple[Any, ...]) -> DType:  # noqa: C901, PLR0912
    """Parse integer type constraints from metadata to determine the most appropriate integer dtype.

    This function examines annotated_types constraints (Gt, Ge, Lt, Le, Interval) to determine
    the smallest integer dtype that can accommodate the specified range.

    Arguments:
        metadata: Tuple of metadata objects, potentially containing annotated_types constraints.

    Returns:
        The most appropriate integer DType based on the constraints.

    Examples:
        >>> from annotated_types import Gt, Interval
        >>> parse_integer_constraints((Gt(0),))  # PositiveInt
        UInt64
        >>> parse_integer_constraints((Interval(ge=-128, le=127),))  # Int8 range
        Int8
    """
    # Extract constraint values safely
    lower_bound = MIN_INT
    upper_bound = MAX_INT

    for item in metadata:
        if isinstance(item, Interval):
            # Handle Interval constraint (e.g., from pydantic conint)
            if item.gt is not None:
                lower_bound = max(lower_bound, int(_extract_numeric_value(item.gt)) + 1)
            if item.ge is not None:
                lower_bound = max(lower_bound, int(_extract_numeric_value(item.ge)))
            if item.lt is not None:
                upper_bound = min(upper_bound, int(_extract_numeric_value(item.lt)) - 1)
            if item.le is not None:
                upper_bound = min(upper_bound, int(_extract_numeric_value(item.le)))

        elif isinstance(item, Gt):
            # Handle Gt constraint (e.g., from pydantic PositiveInt)
            lower_bound = max(lower_bound, int(_extract_numeric_value(item.gt)) + 1)

        elif isinstance(item, Ge):
            # Handle Ge constraint (e.g., from pydantic NonNegativeInt)
            lower_bound = max(lower_bound, int(_extract_numeric_value(item.ge)))

        elif isinstance(item, Lt):
            # Handle Lt constraint
            upper_bound = min(upper_bound, int(_extract_numeric_value(item.lt)) - 1)

        elif isinstance(item, Le):
            # Handle Le constraint
            upper_bound = min(upper_bound, int(_extract_numeric_value(item.le)))

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


def has_integer_constraints(metadata: tuple[Any, ...]) -> bool:
    """Check if metadata contains integer constraints.

    Arguments:
        metadata: Tuple of metadata objects.

    Returns:
        True if metadata contains Gt, Ge, Lt, Le, or Interval constraints, False otherwise.

    Examples:
        >>> from annotated_types import Gt, Interval
        >>> has_integer_constraints((Gt(0),))
        True
        >>> has_integer_constraints(())
        False
    """
    if not metadata:
        return False

    return any(isinstance(item, Gt | Ge | Lt | Le | Interval) for item in metadata)


def parse_multiple_of_constraints(metadata: tuple[Any, ...]) -> bool:
    """Check if metadata contains a MultipleOf constraint.

    Arguments:
        metadata: Tuple of metadata objects.

    Returns:
        True if metadata contains MultipleOf constraint, False otherwise.

    Examples:
        >>> from annotated_types import MultipleOf
        >>> parse_multiple_of_constraints((MultipleOf(5),))
        True
        >>> parse_multiple_of_constraints(())
        False
    """
    if not metadata:
        return False

    return any(isinstance(item, MultipleOf) for item in metadata)


def extract_multiple_of_value(metadata: tuple[Any, ...]) -> int | float | None:
    """Extract the multiple_of value from metadata.

    Arguments:
        metadata: Tuple of metadata objects.

    Returns:
        The multiple_of value, or None if not found.

    Examples:
        >>> from annotated_types import MultipleOf
        >>> extract_multiple_of_value((MultipleOf(5),))
        5
        >>> extract_multiple_of_value(())
        None
    """
    for item in metadata:
        if isinstance(item, MultipleOf):
            return _extract_numeric_value(item.multiple_of)

    return None
