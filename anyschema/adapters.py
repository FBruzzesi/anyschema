# ruff: noqa: E501
from __future__ import annotations

from collections import OrderedDict
from dataclasses import fields as dc_fields
from typing import TYPE_CHECKING, cast

from typing_extensions import get_type_hints

from anyschema._utils import qualified_type_name

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
    `(field_name, field_type, constraints, metadata)` tuples.

    Arguments:
        spec: A mapping from field names to types, or a sequence of `(name, type)` tuples.

    Yields:
        A tuple of `(field_name, field_type, constraints, metadata)` for each field.
        Both constraints and metadata are always empty for this adapter.

    Examples:
        >>> list(into_ordered_dict_adapter({"name": str, "age": int}))
        [('name', <class 'str'>, (), {}), ('age', <class 'int'>, (), {})]

        >>> list(into_ordered_dict_adapter([("age", int), ("name", str)]))
        [('age', <class 'int'>, (), {}), ('name', <class 'str'>, (), {})]
    """
    for field_name, field_type in OrderedDict(spec).items():
        yield field_name, field_type, (), {}


def typed_dict_adapter(spec: TypedDictType) -> FieldSpecIterable:
    """Adapter for TypedDict classes.

    Converts a TypedDict into an iterator yielding field information as
    `(field_name, field_type, constraints, metadata)` tuples.

    Arguments:
        spec: A TypedDict class (not an instance).

    Yields:
        A tuple of `(field_name, field_type, constraints, metadata)` for each field.
        Both constraints and metadata are always empty for this adapter.

    Examples:
        >>> from typing_extensions import TypedDict
        >>>
        >>> class Student(TypedDict):
        ...     name: str
        ...     age: int
        >>>
        >>> list(typed_dict_adapter(Student))
        [('name', <class 'str'>, (), {}), ('age', <class 'int'>, (), {})]
    """
    type_hints = get_type_hints(spec)
    for field_name, field_type in type_hints.items():
        yield field_name, field_type, (), {}


def dataclass_adapter(spec: DataclassType) -> FieldSpecIterable:
    """Adapter for dataclasses.

    Converts a dataclass into an iterator yielding field information as
    `(field_name, field_type, constraints, metadata)` tuples.

    Arguments:
        spec: A dataclass with annotated fields.

    Yields:
        A tuple of `(field_name, field_type, constraints, metadata)` for each field.
        Constraints are always empty, and metadata is extracted from dataclass field.metadata.

    Examples:
        >>> from dataclasses import dataclass, field
        >>>
        >>> @dataclass
        ... class Student:
        ...     name: str
        ...     age: int = field(metadata={"description": "Student age"})
        >>>
        >>> list(dataclass_adapter(Student))
        [('name', <class 'str'>, (), {}), ('age', <class 'int'>, (), {'description': 'Student age'})]
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
        # Extract metadata dict from dataclass field
        # Create a copy to avoid mutating the original dataclass field metadata
        metadata = dict(field.metadata) if field.metadata else {}

        # Python 3.14+ dataclass fields have a doc parameter
        # Check if field has doc attribute and if it's not None
        if (doc := getattr(field, "doc", None)) is not None and ("anyschema/description" not in metadata):
            metadata["anyschema/description"] = doc

        yield field.name, annot_map[field.name], (), metadata


def pydantic_adapter(spec: type[BaseModel]) -> FieldSpecIterable:
    """Adapter for Pydantic BaseModel classes.

    Extracts field information from a Pydantic model class and converts it into an iterator
    yielding field information as `(field_name, field_type, constraints, metadata)` tuples.

    Arguments:
        spec: A Pydantic `BaseModel` class (not an instance).

    Yields:
        A tuple of `(field_name, field_type, constraints, metadata)` for each field.
            - `field_name`: The name of the field as defined in the model
            - `field_type`: The type annotation of the field
            - `constraints`: A tuple of constraint items from `Annotated` types (e.g., `Gt`, `Le`)
            - `metadata`: A dict of custom metadata from `json_schema_extra`

    Examples:
        >>> from pydantic import BaseModel, Field
        >>> from typing import Annotated
        >>>
        >>> class Student(BaseModel):
        ...     name: str = Field(description="Student name")
        ...     age: Annotated[int, Field(ge=0)]
        >>>
        >>> spec_fields = list(pydantic_adapter(Student))
        >>> spec_fields[0]
        ('name', <class 'str'>, (), {'anyschema/description': 'Student name'})
        >>> spec_fields[1]
        ('age', ForwardRef('Annotated[int, Field(ge=0)]', is_class=True), (), {})
    """
    for field_name, field_info in spec.model_fields.items():
        # Extract constraints from metadata (these are the annotated-types constraints)
        constraints = tuple(field_info.metadata)

        json_schema_extra = field_info.json_schema_extra
        # Create a copy of metadata to avoid mutating the original Pydantic Field
        metadata = dict(json_schema_extra) if json_schema_extra and not callable(json_schema_extra) else {}

        # Extract description from Pydantic Field if present and not already in metadata
        if (description := field_info.description) is not None and "anyschema/description" not in metadata:
            metadata["anyschema/description"] = description

        yield field_name, field_info.annotation, constraints, metadata


def attrs_adapter(spec: AttrsClassType) -> FieldSpecIterable:
    """Adapter for attrs classes.

    Extracts field information from an attrs class and converts it into an iterator
    yielding field information as `(field_name, field_type, constraints, metadata)` tuples.

    Arguments:
        spec: An attrs class (not an instance).

    Yields:
        A tuple of `(field_name, field_type, constraints, metadata)` for each field.
            - `field_name`: The name of the field as defined in the attrs class
            - `field_type`: The type annotation of the field
            - `constraints`: Always empty tuple (attrs doesn't use constraints)
            - `metadata`: A dict of custom metadata from the field's metadata dict

    Examples:
        >>> from attrs import define, field
        >>>
        >>> @define
        ... class Student:
        ...     name: str
        ...     age: int = field(metadata={"description": "Student age"})
        >>>
        >>> list(attrs_adapter(Student))
        [('name', <class 'str'>, (), {}), ('age', <class 'int'>, (), {'description': 'Student age'})]
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
        # Create a copy to avoid mutating the original attrs field metadata
        metadata = dict(field.metadata) if field.metadata else {}

        yield field_name, field_type, (), metadata


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
        >>> spec_fields = list(sqlalchemy_adapter(user_table))
        >>> spec_fields[0]
        ('id', Integer(), (), {'anyschema/nullable': False, 'anyschema/unique': False, 'anyschema/description': None})
        >>> spec_fields[1]
        ('name', String(length=50), (), {'anyschema/nullable': True, 'anyschema/unique': False, 'anyschema/description': None})

        >>> from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column  # doctest: +SKIP
        >>>
        >>> class Base(DeclarativeBase):  # doctest: +SKIP
        ...     pass  # doctest: +SKIP
        >>>
        >>> class User(Base):  # doctest: +SKIP
        ...     __tablename__ = "user"  # doctest: +SKIP
        ...     id: Mapped[int] = mapped_column(primary_key=True)  # doctest: +SKIP
        ...     name: Mapped[str]  # doctest: +SKIP
        >>>
        >>> spec_fields = list(sqlalchemy_adapter(User))  # doctest: +SKIP
        >>> spec_fields[0]  # doctest: +SKIP
        ('id', Integer(), (), {'anyschema/nullable': False, 'anyschema/unique': False, 'anyschema/description': None})
        >>> spec_fields[1]  # doctest: +SKIP
        ('name', String(length=50), (), {'anyschema/nullable': True, 'anyschema/unique': False, 'anyschema/description': None})
    """
    from sqlalchemy import Table
    from sqlalchemy.orm import DeclarativeBase

    table: Table
    if isinstance(spec, Table):
        table = spec
    elif isinstance(spec, type) and issubclass(spec, DeclarativeBase):
        table = cast("Table", spec.__table__)
    else:
        msg = f"Expected SQLAlchemy Table or DeclarativeBase subclass, got '{qualified_type_name(spec)}'"
        raise TypeError(msg)

    for column in table.columns:
        anyschema_metadata: dict[str, bool | str | None] = {
            "anyschema/nullable": column.nullable or False,
            "anyschema/unique": column.unique or False,
            "anyschema/description": column.doc or None,
        }
        # Create a copy of column.info to avoid mutating the original SQLAlchemy column
        metadata = anyschema_metadata | dict(column.info)
        yield (column.name, column.type, (), metadata)
