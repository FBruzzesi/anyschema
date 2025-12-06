from __future__ import annotations

from collections import OrderedDict
from dataclasses import fields as dc_fields
from typing import TYPE_CHECKING

from typing_extensions import get_type_hints

if TYPE_CHECKING:
    from pydantic import BaseModel

    from anyschema.typing import (
        AttrsClassType,
        DataclassType,
        FieldSpecIterable,
        IntoOrderedDict,
        SQLAlchemyTableType,
        TypedDictType,
    )

__all__ = (
    "attrs_adapter",
    "dataclass_adapter",
    "into_ordered_dict_adapter",
    "pydantic_adapter",
    "sqlalchemy_adapter",
    "typed_dict_adapter",
)


def into_ordered_dict_adapter(spec: IntoOrderedDict) -> FieldSpecIterable:
    """Adapter for Python mappings and sequences of field definitions.

    Converts a mapping (e.g., `dict`) or sequence of 2-tuples into an iterator yielding field information as
    `(field_name, field_type, metadata)` tuples.

    Arguments:
        spec: A mapping from field names to types, or a sequence of `(name, type)` tuples.

    Yields:
        A tuple of `(field_name, field_type, metadata)` for each field.
        The metadata tuple is always empty `()` for this adapter.

    Examples:
        >>> list(into_ordered_dict_adapter({"name": str, "age": int}))
        [('name', <class 'str'>, ()), ('age', <class 'int'>, ())]

        >>> list(into_ordered_dict_adapter([("age", int), ("name", str)]))
        [('age', <class 'int'>, ()), ('name', <class 'str'>, ())]
    """
    for field_name, field_type in OrderedDict(spec).items():
        yield field_name, field_type, ()


def typed_dict_adapter(spec: TypedDictType) -> FieldSpecIterable:
    """Adapter for TypedDict classes.

    Converts a TypedDict into an iterator yielding field information as
    `(field_name, field_type, metadata)` tuples.

    Arguments:
        spec: A TypedDict class (not an instance).

    Yields:
        A tuple of `(field_name, field_type, metadata)` for each field.
        The metadata tuple is always empty `()` for this adapter.

    Examples:
        >>> from typing_extensions import TypedDict
        >>>
        >>> class Student(TypedDict):
        ...     name: str
        ...     age: int
        >>>
        >>> list(typed_dict_adapter(Student))
        [('name', <class 'str'>, ()), ('age', <class 'int'>, ())]
    """
    type_hints = get_type_hints(spec)
    for field_name, field_type in type_hints.items():
        yield field_name, field_type, ()


def dataclass_adapter(spec: DataclassType) -> FieldSpecIterable:
    """Adapter for dataclasses.

    Converts a dataclass into an iterator yielding field information as
    `(field_name, field_type, metadata)` tuples.

    Arguments:
        spec: A dataclass with annotated fields.

    Yields:
        A tuple of `(field_name, field_type, metadata)` for each field.
        The metadata tuple is always empty `()` for this adapter.

    Examples:
        >>> from dataclasses import dataclass
        >>>
        >>> @dataclass
        ... class Student:
        ...     name: str
        ...     age: int
        >>>
        >>> list(dataclass_adapter(Student))
        [('name', <class 'str'>, ()), ('age', <class 'int'>, ())]
    """
    # get_type_hints eagerly evaluates annotations, which alleviates us from
    #  needing to evaluate ForwardRef's by hand later on.
    annot_map = get_type_hints(spec)

    # Get dataclass fields
    dataclass_fields = dc_fields(spec)
    dataclass_field_names = {field.name for field in dataclass_fields}

    # Check for annotations that aren't dataclass fields
    # This can happen when a class inherits from a dataclass but isn't decorated itself
    if missing_fields := tuple(field for field in annot_map if field not in dataclass_field_names):
        missing_str = ", ".join(f"'{f}'" for f in missing_fields)
        msg = (
            f"Class '{spec.__name__}' has annotations ({missing_str}) that are not dataclass fields. "
            f"If this class inherits from a dataclass, you must also decorate it with @dataclass "
            f"to properly define these fields."
        )
        raise AssertionError(msg)

    for field in dataclass_fields:
        # TODO(unassigned): field.metadata is a mapping, however pydantic has different metadata.
        #  These differences should be smoothed over to create consistent API.
        yield field.name, annot_map[field.name], ()


def pydantic_adapter(spec: type[BaseModel]) -> FieldSpecIterable:
    """Adapter for Pydantic BaseModel classes.

    Extracts field information from a Pydantic model class and converts it into an iterator
    yielding field information as `(field_name, field_type, metadata)` tuples.

    Arguments:
        spec: A Pydantic `BaseModel` class (not an instance).

    Yields:
        A tuple of `(field_name, field_type, metadata)` for each field.
            - `field_name`: The name of the field as defined in the model
            - `field_type`: The type annotation of the field
            - `metadata`: A tuple of metadata items from `Annotated` types or field constraints

    Examples:
        >>> from pydantic import BaseModel, Field
        >>> from typing import Annotated
        >>>
        >>> class Student(BaseModel):
        ...     name: str
        ...     age: Annotated[int, Field(ge=0)]
        >>>
        >>> list(pydantic_adapter(Student))
        [('name', <class 'str'>, ()), ('age', ForwardRef('Annotated[int, Field(ge=0)]', is_class=True), ())]
    """
    for field_name, field_info in spec.model_fields.items():
        yield field_name, field_info.annotation, tuple(field_info.metadata)  # type: ignore[misc]


def attrs_adapter(spec: AttrsClassType) -> FieldSpecIterable:
    """Adapter for attrs classes.

    Extracts field information from an attrs class and converts it into an iterator
    yielding field information as `(field_name, field_type, metadata)` tuples.

    Arguments:
        spec: An attrs class (not an instance).

    Yields:
        A tuple of `(field_name, field_type, metadata)` for each field.
            - `field_name`: The name of the field as defined in the attrs class
            - `field_type`: The type annotation of the field
            - `metadata`: A tuple of metadata items from the field's metadata dict

    Examples:
        >>> from attrs import define
        >>>
        >>> @define
        ... class Student:
        ...     name: str
        ...     age: int
        >>>
        >>> list(attrs_adapter(Student))
        [('name', <class 'str'>, ()), ('age', <class 'int'>, ())]
    """
    import attrs

    # get_type_hints eagerly evaluates annotations, which alleviates us from
    # needing to evaluate ForwardRef's by hand later on.
    # However, it may fail for classes defined in local scopes (e.g., nested classes in functions)
    # so we fall back to using field.type directly if get_type_hints fails.
    try:
        annot_map = get_type_hints(spec)
    except Exception:  # pragma: no cover  # noqa: BLE001
        # If we can't get type hints, use field.type directly
        annot_map = {}

    attrs_fields = attrs.fields(spec)
    attrs_field_names = {field.name for field in attrs_fields}

    # Check for annotations that aren't attrs fields
    # This can happen when a class inherits from an attrs class but isn't decorated itself
    if annot_map and (missing_fields := tuple(field for field in annot_map if field not in attrs_field_names)):
        missing_str = ", ".join(f"'{f}'" for f in sorted(missing_fields))
        msg = (
            f"Class '{spec.__name__}' has annotations ({missing_str}) that are not attrs fields. "
            f"If this class inherits from an attrs class, you must also decorate it with @attrs.define "
            f"or @attrs.frozen to properly define these fields."
        )
        raise AssertionError(msg)

    for field in attrs_fields:
        field_name = field.name
        field_type = annot_map.get(field_name, field.type)

        # Extract metadata if present - attrs stores it as a mapping
        # We convert it to a tuple for consistency with other adapters
        metadata = tuple(field.metadata.values()) if field.metadata else ()

        yield field_name, field_type, metadata


def sqlalchemy_adapter(spec: SQLAlchemyTableType) -> FieldSpecIterable:
    """Adapter for SQLAlchemy tables.

    Extracts field information from a SQLAlchemy Table (Core) or DeclarativeBase class (ORM)
    and converts it into an iterator yielding field information as `(field_name, field_type, metadata)` tuples.

    Arguments:
        spec: A SQLAlchemy Table instance or DeclarativeBase subclass.

    Yields:
        A tuple of `(field_name, field_type, metadata)` for each column.
            - `field_name`: The name of the column
            - `field_type`: The SQLAlchemy column type
            - `metadata`: A tuple containing column metadata (nullable, etc.)

    Examples:
        >>> from sqlalchemy import Table, Column, Integer, String, MetaData
        >>>
        >>> metadata = MetaData()
        >>> user_table = Table(
        ...     "user",
        ...     metadata,
        ...     Column("id", Integer, primary_key=True),
        ...     Column("name", String(50)),
        ... )
        >>>
        >>> list(sqlalchemy_adapter(user_table))
        [('id', Integer(), ()), ('name', String(50), ())]

        >>> from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
        >>>
        >>> class Base(DeclarativeBase):
        ...     pass
        >>>
        >>> class User(Base):
        ...     __tablename__ = "user"
        ...     id: Mapped[int] = mapped_column(primary_key=True)
        ...     name: Mapped[str]
        >>>
        >>> list(sqlalchemy_adapter(User))
        [('id', Integer(), ()), ('name', String(), ())]
    """
    from sqlalchemy import Table
    from sqlalchemy.orm import DeclarativeBase

    table: Table
    if isinstance(spec, Table):
        table = spec
    elif isinstance(spec, type) and issubclass(spec, DeclarativeBase):
        table = spec.__table__
    else:  # pragma: no cover
        msg = f"Expected SQLAlchemy Table or DeclarativeBase subclass, got {type(spec)}"
        raise TypeError(msg)

    for column in table.columns:
        yield column.name, column.type, (column.nullable,)
