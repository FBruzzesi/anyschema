from __future__ import annotations

from typing import Any


def qualified_type_name(obj: object | type[Any], /) -> str:
    tp = obj if isinstance(obj, type) else type(obj)
    module = tp.__module__ if tp.__module__ != "builtins" else ""
    return f"{module}.{tp.__name__}".lstrip(".")
