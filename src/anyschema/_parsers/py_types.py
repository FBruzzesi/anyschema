from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from decimal import Decimal as PyDecimal
from types import NoneType
from types import UnionType
from typing import TYPE_CHECKING
from typing import Any
from typing import Final
from typing import GenericAlias
from typing import Union
from typing import _GenericAlias
from typing import get_args
from typing import get_origin

import narwhals as nw

if TYPE_CHECKING:
    from narwhals.dtypes import DType


PY_TYPE_TO_NW_DTYPE: Final[dict[type, DType]] = {
    bool: nw.Boolean(),
    bytes: nw.Binary(),
    date: nw.Date(),
    datetime: nw.Datetime(),
    float: nw.Float64(),
    int: nw.Int64(),
    str: nw.String(),
    time: nw.Time(),
    timedelta: nw.Duration(),
}
"""Mapping of Python built-in types to Narwhals dtypes"""

def is_optional_type(annotation: type[Any]) -> bool:
    """Check if a type annotation represents an Optional type (Union with None).
    
    Arguments:
        annotation: The type annotation to check.
        
    Returns:
        True if the annotation is Optional (Union[T, None]), False otherwise.
    """
    origin = get_origin(annotation)
    if origin not in (Union, UnionType):
        return False

    args = get_args(annotation)
    return len(args) == 2 and NoneType in args  # noqa: PLR2004


def unwrap_optional(annotation: type[Any]) -> tuple[type[Any], tuple[Any, ...]]:
    """Unwrap an Optional type to get the underlying type and metadata.
    
    Arguments:
        annotation: The type annotation to unwrap.
        
    Returns:
        A tuple of (underlying_type, metadata).
    """
    if not is_optional_type(annotation):
        return annotation, ()
    
    args = get_args(annotation)
    non_none_type = args[0] if args[1] is NoneType else args[1]
    
    # Extract metadata if present (for Annotated types)
    origin = getattr(non_none_type, "__origin__", None)
    metadata = getattr(non_none_type, "__metadata__", ())
    
    if origin is not None:
        # For Annotated types, get the base type
        inner_args = getattr(non_none_type, "__args__", (non_none_type,))
        return inner_args[0], metadata
    
    return non_none_type, metadata


def parse_py_type_into_dtype(type_annotation: type[Any], metadata: tuple[Any, ...] = ()) -> DType | None:
    """Parse Python types to Narwhals dtypes.

    This function handles core Python types without any library-specific logic.
    It returns None if the type is not a basic Python type, allowing other
    parsers to handle it.
    
    Arguments:
        type_annotation: The Python type to parse.
        metadata: Optional metadata associated with the type.
        
    Returns:
        A Narwhals DType if the type is recognized, None otherwise.
    """
    return PY_TYPE_TO_NW_DTYPE.get(type_annotation)


def parse_list_type(annotation: type[Any]) -> tuple[type[Any], tuple[Any, ...]] | None:
    """Parse list type annotations and extract the inner type.
    
    Arguments:
        annotation: The type annotation to parse.
        
    Returns:
        A tuple of (inner_type, metadata) if annotation is a list type, None otherwise.
    """
    origin = get_origin(annotation)
    
    if origin is not list:
        return None
    
    args = get_args(annotation)
    if not args:
        return None
    
    inner_type = args[0]
    
    # Handle Optional inner type
    if is_optional_type(inner_type):
        inner_type, metadata = unwrap_optional(inner_type)
        return inner_type, metadata
    
    return inner_type, ()


__all__ = (
    "is_optional_type",
    "unwrap_optional", 
    "parse_py_type_into_dtype",
    "parse_list_type",
)
