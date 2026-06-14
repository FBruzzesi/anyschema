# ruff: noqa: T201
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from typing_extensions import TypeIs

_T = TypeVar("_T")


def qualified_type_name(obj: object | type[Any], /) -> str:
    # Copied from Narwhals: https://github.com/narwhals-dev/narwhals/blob/282a3cb08f406e2f319d86b81a7300a2a6c5f390/narwhals/_utils.py#L1922
    # Author: Marco Gorelli
    # License: MIT: https://github.com/narwhals-dev/narwhals/blob/282a3cb08f406e2f319d86b81a7300a2a6c5f390/LICENSE.md
    tp = obj if isinstance(obj, type) else type(obj)
    module = tp.__module__ if tp.__module__ != "builtins" else ""
    return f"{module}.{tp.__name__}".lstrip(".")


def _get_sys_info() -> dict[str, str]:
    """System information.

    Returns system and Python version information

    Adapted from sklearn.

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
