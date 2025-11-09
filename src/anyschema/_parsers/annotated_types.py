from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import narwhals as nw
from annotated_types import Ge
from annotated_types import Gt
from annotated_types import Interval

from anyschema._utils import INT_RANGES
from anyschema._utils import MAX_INT
from anyschema._utils import MIN_INT
from anyschema._utils import UINT_RANGES

if TYPE_CHECKING:
    from narwhals.dtypes import DType


def parse_integer_constraints(metadata: tuple[Any, ...]) -> DType:
    """Parse integer type constraints from metadata to determine the most appropriate integer dtype.
    
    This function examines annotated_types constraints (Gt, Ge, Interval) to determine
    the smallest integer dtype that can accommodate the specified range.
    
    Arguments:
        metadata: Tuple of metadata objects, potentially containing annotated_types constraints.
        
    Returns:
        The most appropriate integer DType based on the constraints.
    """
    match metadata:
        # Handle Interval constraint (e.g., from pydantic conint)
        case (_, Interval(gt=gt, ge=ge, lt=lt, le=le), _):
            lower_bound = max((gt + 1 if gt is not None else MIN_INT), (ge if ge is not None else MIN_INT))
            upper_bound = min((lt - 1 if lt is not None else MAX_INT), (le if le is not None else MAX_INT))

            # Choose between signed and unsigned based on lower_bound
            if lower_bound >= 0:
                # Range is non-negative, use unsigned integers (smaller memory footprint)
                for dtype, (min_val, max_val) in UINT_RANGES.items():
                    if upper_bound <= max_val:
                        return dtype
                # If no unsigned type fits, fall back to signed
                return nw.UInt64()
            else:
                # Range includes negative values, use signed integers
                for dtype, (min_val, max_val) in INT_RANGES.items():
                    if lower_bound >= min_val and upper_bound <= max_val:
                        return dtype
                return nw.Int64()

        # Handle single Gt or Ge constraint (e.g., from pydantic PositiveInt, NonNegativeInt)
        case (Gt(gt=value),) | (Ge(ge=value),):
            return nw.UInt64() if value >= 0 else nw.Int64()

        # All other cases: default to Int64
        case _:
            return nw.Int64()


def has_integer_constraints(metadata: tuple[Any, ...]) -> bool:
    """Check if metadata contains integer constraints.
    
    Arguments:
        metadata: Tuple of metadata objects.
        
    Returns:
        True if metadata contains Gt, Ge, or Interval constraints, False otherwise.
    """
    if not metadata:
        return False
    
    for item in metadata:
        if isinstance(item, (Gt, Ge, Interval)):
            return True
    
    return False


__all__ = (
    "parse_integer_constraints",
    "has_integer_constraints",
    "INT_RANGES",
)
