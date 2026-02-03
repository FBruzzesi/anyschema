from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass as dc_is_dataclass
from importlib.metadata import version as get_version
from importlib.util import find_spec
from typing import TYPE_CHECKING, TypeAlias

from narwhals.utils import parse_version
from typing_extensions import TypeIs, is_typeddict

if TYPE_CHECKING:
    from types import ModuleType

    from pydantic import BaseModel

    from anyschema.typing import AttrsClassType, DataclassType, IntoOrderedDict, SQLAlchemyTableType, TypedDictType

    Version: TypeAlias = tuple[int, ...]

MIN_VERSIONS: dict[str, Version] = {
    "attrs": (22, 1),
    "pydantic": (2, 0),
    "sqlalchemy": (2, 0),
}
"""Minimum required versions for optional dependencies"""


def check_version(package: str) -> bool:
    """Check if a package is installed and meets the minimum version requirement.

    Arguments:
        package: Name of the package to check.

    Returns:
        True if the package is installed and meets the minimum version requirement.

    Raises:
        ImportError: If the package is installed but does not meet the minimum version.
    """
    # Not installed case
    if find_spec(package) is None:
        return False

    # Installed & no min version requirement case
    if (min_version := MIN_VERSIONS.get(package)) is None:
        return True

    installed_version = get_version(package)
    if parse_version(installed_version) < min_version:
        min_version_str = ".".join(str(v) for v in min_version)
        msg = f"anyschema requires {package}>={min_version_str}, but version {installed_version} is installed."
        raise ImportError(msg)

    return True


ANNOTATED_TYPES_AVAILABLE = find_spec("annotated_types") is not None
PYDANTIC_AVAILABLE = check_version("pydantic")
ATTRS_AVAILABLE = check_version("attrs")
SQLALCHEMY_AVAILABLE = check_version("sqlalchemy")


def get_pydantic() -> ModuleType | None:
    """Get pydantic module (if already imported - else return None)."""
    return sys.modules.get("pydantic", None)


def get_attrs() -> ModuleType | None:
    """Get attrs module (if already imported - else return None)."""
    return sys.modules.get("attrs", None)


def is_into_ordered_dict(obj: object) -> TypeIs[IntoOrderedDict]:
    """Check if the object can be converted into a python OrderedDict."""
    tpl_size = 2
    return isinstance(obj, Mapping) or (
        isinstance(obj, Sequence) and all(isinstance(s, tuple) and len(s) == tpl_size for s in obj)
    )


def is_typed_dict(obj: object) -> TypeIs[TypedDictType]:
    """Check if the object is a TypedDict and narrows type checkers."""
    return is_typeddict(obj)


def is_dataclass(obj: object) -> TypeIs[DataclassType]:
    """Check if the object is a dataclass and narrows type checkers."""
    return dc_is_dataclass(obj)


def is_pydantic_base_model(obj: object) -> TypeIs[type[BaseModel]]:
    """Check if the object is a pydantic BaseModel."""
    return (
        (pydantic := get_pydantic()) is not None
        and isinstance(obj, type)
        and isinstance(obj, type(pydantic.BaseModel))
        and issubclass(obj, pydantic.BaseModel)
    )


def is_attrs_class(obj: object) -> TypeIs[AttrsClassType]:
    """Check if the object is an attrs class.

    Uses attrs.has() to check if a class is an attrs class.
    Supports @attrs.define/@attrs.frozen decorators.
    """
    return (attrs := get_attrs()) is not None and attrs.has(obj)


def get_sqlalchemy() -> ModuleType | None:
    """Get sqlalchemy module (if already imported - else return None)."""
    return sys.modules.get("sqlalchemy", None)


def get_sqlalchemy_orm() -> ModuleType | None:
    """Get sqlalchemy.orm module (if already imported - else return None)."""
    return sys.modules.get("sqlalchemy.orm", None)


def is_sqlalchemy_table(obj: object) -> TypeIs[SQLAlchemyTableType]:
    """Check if the object is a SQLAlchemy Table or DeclarativeBase class.

    Supports both:

    - SQLAlchemy Table instances (Core)
    - SQLAlchemy ORM mapped classes (DeclarativeBase subclasses)
    """
    is_table = (sql := get_sqlalchemy()) is not None and isinstance(obj, sql.Table)
    is_declarative_base = (
        (sql_orm := get_sqlalchemy_orm()) is not None
        and isinstance(obj, type)
        and issubclass(obj, sql_orm.DeclarativeBase)
    )
    return is_table or is_declarative_base
