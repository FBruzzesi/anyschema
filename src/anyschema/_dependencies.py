from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType


def get_pydantic() -> ModuleType | None:  # pragma: no cover
    """Get pydantic module (if already imported - else return None)."""
    return sys.modules.get("pydantic", None)
