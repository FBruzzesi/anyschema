from __future__ import annotations

import sys
from importlib.metadata import version
from importlib.util import find_spec
from typing import TYPE_CHECKING

from narwhals.utils import parse_version

if TYPE_CHECKING:
    from types import ModuleType

_ANNOTATED_TYPES_AVAILABLE = find_spec("annotated_types") is not None

_PYDANTIC_AVAILABLE = find_spec("pydantic") is not None
_PYDANTIC_VERSION = parse_version(version("pydantic")) if _PYDANTIC_AVAILABLE else None


def get_pydantic() -> ModuleType | None:  # pragma: no cover
    """Get pydantic module (if already imported - else return None)."""
    return sys.modules.get("pydantic", None)
