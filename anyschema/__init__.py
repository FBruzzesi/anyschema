from __future__ import annotations

import typing as _t

from anyschema._anyschema import AnySchema, Field
from anyschema._utils import show_versions

__all__ = ("AnySchema", "Field", "show_versions")
__title__ = __name__
__version__: str


if not _t.TYPE_CHECKING:

    def __getattr__(name: str) -> _t.Any:
        if name == "__version__":
            global __version__  # noqa: PLW0603

            from importlib import metadata

            __version__ = metadata.version(__name__)
            return __version__
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
else:  # pragma: no cover
    ...
