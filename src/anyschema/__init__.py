from __future__ import annotations

from importlib import metadata

from anyschema._anyschema import AnySchema

__title__ = __name__
__version__ = metadata.version(__title__)

__all__ = ("AnySchema",)
