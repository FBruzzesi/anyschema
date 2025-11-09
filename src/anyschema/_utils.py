from __future__ import annotations

from types import NoneType, UnionType
from typing import TYPE_CHECKING, Any, Final, TypeAlias, Union, get_args, get_origin

import narwhals as nw

from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    LowerBound: TypeAlias = int
    UpperBound: TypeAlias = int
    Range: TypeAlias = tuple[LowerBound, UpperBound]


__all__ = ("INT_RANGES", "MAX_INT", "MIN_INT", "UINT_RANGES", "is_optional_type", "parse_union", "unwrap_optional")


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


def parse_union(union: tuple[type[Any], ...]) -> tuple[type[Any], tuple[Any, ...]]:
    if len(union) != 2:  # noqa: PLR2004
        msg = "Union with more than two types is not supported."
        raise UnsupportedDTypeError(msg)

    _field0, _field1 = union

    if _field0 is not NoneType and _field1 is not NoneType:
        msg = "Union with both types being not None is not supported."
        raise UnsupportedDTypeError(msg)

    _field = _field1 if _field0 is NoneType else _field0
    _origin: type | None = getattr(_field, "__origin__", None)
    _type: type = getattr(_field, "__args__", (_field,))[0]
    _metadata: tuple[Any, ...] = getattr(_field, "__metadata__", ())

    return (_field, _metadata) if _origin is not None else (_type, _metadata)


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
