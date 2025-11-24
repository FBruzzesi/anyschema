from __future__ import annotations

from typing import Any


def qualified_type_name(obj: object | type[Any], /) -> str:
    # Copied from Narwhals: https://github.com/narwhals-dev/narwhals/blob/282a3cb08f406e2f319d86b81a7300a2a6c5f390/narwhals/_utils.py#L1922
    # Author: Marco Gorelli
    # License: MIT: https://github.com/narwhals-dev/narwhals/blob/282a3cb08f406e2f319d86b81a7300a2a6c5f390/LICENSE.md
    tp = obj if isinstance(obj, type) else type(obj)
    module = tp.__module__ if tp.__module__ != "builtins" else ""
    return f"{module}.{tp.__name__}".lstrip(".")
