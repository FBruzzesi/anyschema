from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from types import ModuleType

    from pydantic import BaseModel


def get_pydantic() -> ModuleType | None:  # pragma: no cover
    """Get pydantic module (if already imported - else return None)."""
    return sys.modules.get("pydantic", None)


def is_pydantic_base_model(obj: object) -> TypeGuard[type[BaseModel]]:
    return (pydantic := get_pydantic()) is not None and (isinstance(obj, type) and issubclass(obj, pydantic.BaseModel))
