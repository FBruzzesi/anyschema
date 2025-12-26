from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass as dc_is_dataclass
from importlib.util import find_spec
from typing import TYPE_CHECKING

from typing_extensions import TypeIs, is_typeddict

if TYPE_CHECKING:
    from types import ModuleType

    from anyschema.typing import (
        AttrsClassType,
        DataclassType,
        IntoOrderedDict,
        MarshmallowSchemaType,
        PydanticBaseModelType,
        SQLAlchemyTableType,
        TypedDictType,
    )

ANNOTATED_TYPES_AVAILABLE = find_spec("annotated_types") is not None
ATTRS_AVAILABLE = find_spec("attrs") is not None
MARSHMALLOW_AVAILABLE = find_spec("marshmallow") is not None
PYDANTIC_AVAILABLE = find_spec("pydantic") is not None
SQLALCHEMY_AVAILABLE = find_spec("sqlalchemy") is not None


def get_pydantic() -> ModuleType | None:
    """Get pydantic module (if already imported - else return None)."""
    return sys.modules.get("pydantic", None)


def get_attrs() -> ModuleType | None:
    """Get attrs module (if already imported - else return None)."""
    return sys.modules.get("attrs", None)


def get_marshmallow() -> ModuleType | None:
    """Get marshmallow module (if already imported - else return None)."""
    return sys.modules.get("marshmallow", None)


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


def is_pydantic_base_model(obj: object) -> TypeIs[PydanticBaseModelType]:
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


def is_marshmallow_schema(obj: object) -> TypeIs[MarshmallowSchemaType]:
    """Check if the object is a marshmallow Schema class."""
    return (
        (marshmallow := get_marshmallow()) is not None and isinstance(obj, type) and issubclass(obj, marshmallow.Schema)
    )
