from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from types import ModuleType

    from pydantic import BaseModel

    from anyschema.typing import IntoOrderedDict


def get_pydantic() -> ModuleType | None:  # pragma: no cover
    """Get pydantic module (if already imported - else return None)."""
    return sys.modules.get("pydantic", None)


def is_pydantic_base_model(obj: object) -> TypeGuard[type[BaseModel]]:
    return (pydantic := get_pydantic()) is not None and (isinstance(obj, type) and issubclass(obj, pydantic.BaseModel))


def is_into_ordered_dict(obj: object) -> TypeGuard[IntoOrderedDict]:
    sequence_size = 2
    return isinstance(obj, Mapping) or (isinstance(obj, Sequence) and all(len(s) == sequence_size for s in obj))
