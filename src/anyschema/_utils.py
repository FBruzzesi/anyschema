# ruff: noqa: T201
from __future__ import annotations

from types import UnionType
from typing import TYPE_CHECKING, Any, Final, Union

import narwhals as nw
from typing_extensions import get_origin  # noqa: UP035

if TYPE_CHECKING:
    from narwhals.dtypes import IntegerType, SignedIntegerType, UnsignedIntegerType

UINT_RANGES: Final[dict[UnsignedIntegerType, tuple[int, int]]] = {
    nw.UInt8(): (0, 255),
    nw.UInt16(): (0, 65535),
    nw.UInt32(): (0, 4294967295),
    nw.UInt64(): (0, 18446744073709551615),
}
"""Inclusive unsigned integer ranges, in ascending order so the first fit is the smallest."""

INT_RANGES: Final[dict[SignedIntegerType, tuple[int, int]]] = {
    nw.Int8(): (-128, 127),
    nw.Int16(): (-32768, 32767),
    nw.Int32(): (-2147483648, 2147483647),
    nw.Int64(): (-9223372036854775808, 9223372036854775807),
}
"""Inclusive signed integer ranges, in ascending order so the first fit is the smallest."""

INT64_MIN: Final[int] = -9_223_372_036_854_775_808
UINT64_MAX: Final[int] = 18_446_744_073_709_551_615


def is_union_type(tp: object) -> bool:
    """Whether `tp` is a union type: `X | Y`, `Union[X, Y]` or `Optional[X]`."""
    return get_origin(tp) is Union or isinstance(tp, UnionType)


def int_dtype_from_bounds(lower_bound: int, upper_bound: int) -> IntegerType:
    """Return the smallest Narwhals integer dtype that fits the inclusive `[lower_bound, upper_bound]` range.

    Unsigned dtypes are used when `lower_bound >= 0`. A range that fits no dtype falls back to `UInt64` or `Int64`.

    Examples:
        >>> int_dtype_from_bounds(0, 255)
        UInt8
        >>> int_dtype_from_bounds(-1, 1000)
        Int16
    """
    if lower_bound >= 0:
        return next((dtype for dtype, (_, upper) in UINT_RANGES.items() if upper_bound <= upper), nw.UInt64())
    return next(
        (dtype for dtype, (lower, upper) in INT_RANGES.items() if lower <= lower_bound and upper_bound <= upper),
        nw.Int64(),
    )


def qualified_type_name(obj: object | type[Any], /) -> str:
    # Copied from Narwhals: https://github.com/narwhals-dev/narwhals/blob/282a3cb08f406e2f319d86b81a7300a2a6c5f390/narwhals/_utils.py#L1922
    # Author: Marco Gorelli
    # License: MIT: https://github.com/narwhals-dev/narwhals/blob/282a3cb08f406e2f319d86b81a7300a2a6c5f390/LICENSE.md
    tp = obj if isinstance(obj, type) else type(obj)
    module = tp.__module__ if tp.__module__ != "builtins" else ""
    return f"{module}.{tp.__name__}".lstrip(".")


def _get_sys_info() -> dict[str, str]:
    """System information.

    Returns system and Python version information. Adapted from sklearn.

    Returns:
        Dictionary with system info.
    """
    import platform
    import sys

    python = sys.version.replace("\n", " ")

    blob = (
        ("python", python),
        ("machine", platform.platform()),
    )

    return dict(blob)


def _get_deps_info() -> dict[str, str]:
    """Overview of the installed version of main dependencies.

    This function does not import the modules to collect the version numbers
    but instead relies on standard Python package metadata.

    Returns version information on relevant Python libraries

    This function and show_versions were copied from sklearn and adapted

    Returns:
        Mapping from dependency to version.
    """
    from importlib.metadata import distributions

    libs = (
        "anyschema",
        "narwhals",
        "typing_extensions",
        "attrs",
        "pydantic",
        "sqlalchemy",
        "pandas",
        "polars",
        "pyarrow",
    )
    dist_map = {dist.name.lower(): dist.version for dist in distributions()}
    return {lib: dist_map.get(lib, "") for lib in libs}


def show_versions() -> None:
    """Print useful debugging information.

    Examples:
        >>> from anyschema import show_versions
        >>> show_versions()  # doctest: +SKIP
    """
    sys_info = _get_sys_info()
    deps_info = _get_deps_info()

    print("\nSystem:")
    for k, stat in sys_info.items():
        print(f"{k:>10}: {stat}")

    print("\nPython dependencies:")
    for k, stat in deps_info.items():
        print(f"{k:>20}: {stat}")
