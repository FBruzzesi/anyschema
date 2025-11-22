from __future__ import annotations

import typing as _t

from anyschema._anyschema import AnySchema

__all__ = ("AnySchema",)
__title__ = __name__
__version__: str


def __getattr__(name: _t.Literal["__version__"]) -> str:  # type: ignore[misc]
    if name == "__version__":
        global __version__  # noqa: PLW0603

        from importlib import metadata

        __version__ = metadata.version(__name__)
        return __version__
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
