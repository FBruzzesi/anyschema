# ruff: noqa: T201
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Final, TypeVar

import narwhals as nw

if TYPE_CHECKING:
    from narwhals.dtypes import DType
    from typing_extensions import TypeIs

_T = TypeVar("_T")

UINT_RANGES: Final[dict[DType, tuple[int, int]]] = {
    nw.UInt8(): (0, 255),
    nw.UInt16(): (0, 65535),
    nw.UInt32(): (0, 4294967295),
    nw.UInt64(): (0, 18446744073709551615),
}
"""Unsigned integer ranges, both included, sorted by upper bound ascending for smallest-fit selection."""

INT_RANGES: Final[dict[DType, tuple[int, int]]] = {
    nw.Int8(): (-128, 127),
    nw.Int16(): (-32768, 32767),
    nw.Int32(): (-2147483648, 2147483647),
    nw.Int64(): (-9223372036854775808, 9223372036854775807),
}
"""Signed integer ranges, both included, sorted by upper bound ascending for smallest-fit selection."""

MIN_INT: Final[int] = -9_223_372_036_854_775_808
MAX_INT: Final[int] = 18_446_744_073_709_551_615


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


def is_sequence_but_not_str(sequence: Sequence[_T] | Any) -> TypeIs[Sequence[_T]]:
    return isinstance(sequence, Sequence) and not isinstance(sequence, str)


def is_sequence_of(obj: Any, tp: type[_T]) -> TypeIs[Sequence[_T]]:
    # Check if an object is a sequence of `tp`, only sniffing the first element.
    return bool(is_sequence_but_not_str(obj) and (first := next(iter(obj), None)) and isinstance(first, tp))


def int_dtype_from_bounds(lower_bound: int, upper_bound: int) -> DType:
    """Return the smallest Narwhals integer dtype that fits the inclusive `[lower_bound, upper_bound]` range.

    Unsigned dtypes are preferred whenever `lower_bound >= 0`. Ranges that do not fit any dtype fall back to
    `UInt64` (non-negative) or `Int64`.

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
