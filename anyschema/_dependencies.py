from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass as dc_is_dataclass
from importlib.util import find_spec
from typing import TYPE_CHECKING, TypeGuard, cast

if TYPE_CHECKING:
    from types import ModuleType

    from pydantic import BaseModel

    from anyschema.typing import DataclassType, IntoOrderedDict

ANNOTATED_TYPES_AVAILABLE = find_spec("annotated_types") is not None
PYDANTIC_AVAILABLE = find_spec("pydantic") is not None


def get_pydantic() -> ModuleType | None:  # pragma: no cover
    """Get pydantic module (if already imported - else return None)."""
    return sys.modules.get("pydantic", None)


def is_pydantic_base_model(obj: object) -> TypeGuard[type[BaseModel]]:
    """Check if the object is a pydantic BaseModel."""
    return (
        (pydantic := get_pydantic()) is not None
        and isinstance(obj, cast("type", type(pydantic.BaseModel)))
        and issubclass(obj, pydantic.BaseModel)  # type: ignore[arg-type]
    )


def is_into_ordered_dict(obj: object) -> TypeGuard[IntoOrderedDict]:
    """Check if the object can be converted into a python OrderedDict."""
    tpl_size = 2
    return isinstance(obj, Mapping) or (
        isinstance(obj, Sequence) and all(isinstance(s, tuple) and len(s) == tpl_size for s in obj)
    )


def is_dataclass(obj: object) -> TypeGuard[DataclassType]:
    """Check if the object is a dataclass and narrows type checkers."""
    return dc_is_dataclass(obj)
