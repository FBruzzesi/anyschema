from __future__ import annotations

import sys
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass as dc_is_dataclass
from importlib.metadata import version as get_version
from importlib.util import find_spec
from typing import TYPE_CHECKING, TypeAlias, TypeGuard

from narwhals.utils import parse_version
from typing_extensions import TypeIs, is_typeddict

if TYPE_CHECKING:
    from pydantic import BaseModel
    from pydantic_extra_types.color import Color

    from anyschema.typing import (
        AttrsClassType,
        DataclassType,
        IntoOrderedDict,
        JsonSchema,
        SQLAlchemyTableType,
        TypedDictType,
    )

    Version: TypeAlias = tuple[int, ...]

MIN_VERSIONS: dict[str, Version] = {
    "attrs": (22, 1),
    "pydantic": (2, 0),
    "sqlalchemy": (2, 0),
}
"""Minimum required versions for optional dependencies"""


def check_version(package: str) -> bool:
    """Check if a package is installed and meets the minimum version anyschema supports.

    Arguments:
        package: Name of the package to check.

    Returns:
        True if the package is installed and meets the minimum version.

    Warns:
        UserWarning: If the package is older than the minimum. anyschema then treats it as not installed.
    """
    if find_spec(package) is None:
        return False

    if (min_version := MIN_VERSIONS.get(package)) is None:
        return True

    installed_version = get_version(package)
    if parse_version(installed_version) < min_version:
        min_version_str = ".".join(str(v) for v in min_version)
        msg = (
            f"anyschema requires {package}>={min_version_str}, but version {installed_version} is installed. "
            "anyschema will ignore it."
        )
        warnings.warn(msg, stacklevel=2)
        return False

    return True


ANNOTATED_TYPES_AVAILABLE = find_spec("annotated_types") is not None
PYDANTIC_AVAILABLE = check_version("pydantic")
ATTRS_AVAILABLE = check_version("attrs")
SQLALCHEMY_AVAILABLE = check_version("sqlalchemy")


def is_into_ordered_dict(obj: object) -> TypeIs[IntoOrderedDict]:
    """Check if the object can be converted into a python OrderedDict."""
    tpl_size = 2
    return isinstance(obj, Mapping) or (
        isinstance(obj, Sequence) and all(isinstance(s, tuple) and len(s) == tpl_size for s in obj)
    )


def is_jsonschema(obj: object) -> TypeIs[JsonSchema]:
    """Check if the object looks like a JSON Schema object.

    That is a mapping with either a `"properties"` mapping and `"type": "object"` (or no `type`), or a root `"$ref"`
    (or `"allOf"`, before Pydantic 2.9) next to `"$defs"`, as Pydantic emits for self-referencing models.
    """
    if not isinstance(obj, Mapping):
        return False
    if isinstance(obj.get("$defs"), Mapping) and (
        isinstance(obj.get("$ref"), str) or isinstance(obj.get("allOf"), list)
    ):
        return True
    return isinstance(obj.get("properties"), Mapping) and obj.get("type", "object") == "object"


# `TypeGuard`, not `TypeIs`: `type[Any]` matches these protocols, so `TypeIs` narrows the False branch to `Never`.
def is_typed_dict(obj: object) -> TypeGuard[TypedDictType]:
    """Check if the object is a TypedDict and narrows type checkers."""
    return is_typeddict(obj)


def is_dataclass(obj: object) -> TypeGuard[DataclassType]:
    """Check if the object is a dataclass and narrows type checkers."""
    return dc_is_dataclass(obj)


def is_pydantic_base_model(obj: object) -> TypeIs[type[BaseModel]]:
    """Check if the object is a pydantic BaseModel."""
    return (
        PYDANTIC_AVAILABLE
        and (pydantic := sys.modules.get("pydantic")) is not None
        and isinstance(obj, type)
        # On Python 3.10 `list[int]` passes the check above, and with pydantic 2.0 `issubclass` then raises.
        and isinstance(obj, type(pydantic.BaseModel))
        and issubclass(obj, pydantic.BaseModel)
    )


def is_pydantic_extra_types_color(obj: object) -> TypeIs[type[Color]]:
    """Check if the object is `pydantic_extra_types.color.Color` or a subclass of it."""
    return (
        (color_module := sys.modules.get("pydantic_extra_types.color")) is not None
        and isinstance(obj, type)
        and issubclass(obj, color_module.Color)
    )


def is_attrs_class(obj: object) -> TypeIs[AttrsClassType]:
    """Check if the object is an attrs class.

    Uses attrs.has() to check if a class is an attrs class.
    Supports @attrs.define/@attrs.frozen decorators.
    """
    return ATTRS_AVAILABLE and (attrs := sys.modules.get("attrs")) is not None and attrs.has(obj)


def is_sqlalchemy_table(obj: object) -> TypeIs[SQLAlchemyTableType]:
    """Check if the object is a SQLAlchemy Table or DeclarativeBase class.

    Supports both:

    - SQLAlchemy Table instances (Core)
    - SQLAlchemy ORM mapped classes (DeclarativeBase subclasses)
    """
    if not SQLALCHEMY_AVAILABLE:
        return False
    is_table = (sql := sys.modules.get("sqlalchemy")) is not None and isinstance(obj, sql.Table)
    is_declarative_base = (
        (sql_orm := sys.modules.get("sqlalchemy.orm")) is not None
        and isinstance(obj, type)
        and issubclass(obj, sql_orm.DeclarativeBase)
    )
    return is_table or is_declarative_base
