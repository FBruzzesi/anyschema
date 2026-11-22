from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import fields as dc_fields
from typing import TYPE_CHECKING, Any, ClassVar, Literal, get_origin

from typing_extensions import get_type_hints

from anyschema._dependencies import is_jsonschema
from anyschema._jsonschema import allows_null, extract_field_metadata, inline_refs
from anyschema._metadata import get_anyschema_value_by_key, set_anyschema_meta

if TYPE_CHECKING:
    from collections.abc import Container

    from pydantic import BaseModel

    from anyschema.typing import (
        AttrsClassType,
        DataclassType,
        FieldSpecIterable,
        IntoOrderedDict,
        JsonSchema,
        SQLAlchemyTableType,
        TypedDictType,
    )

__all__ = (
    "attrs_adapter",
    "dataclass_adapter",
    "into_ordered_dict_adapter",
    "jsonschema_adapter",
    "pydantic_adapter",
    "sqlalchemy_adapter",
    "typed_dict_adapter",
)


def jsonschema_adapter(spec: JsonSchema) -> FieldSpecIterable:
    """Adapter for JSON Schema objects, such as the output of `pydantic.BaseModel.model_json_schema()`.

    Each property is yielded with its subschema as the field type, with every local `$ref` inlined, for
    [`JsonSchemaStep`][anyschema.parsers.JsonSchemaStep] to convert.

    A field is nullable only when its schema allows `null`: a `null` branch in `anyOf`/`oneOf`, `"null"` in a `type`
    list, or `null` in `enum`. The `required` keyword does not affect nullability.

    Arguments:
        spec: A JSON Schema with a `"properties"` mapping and `"type": "object"` (or no `type`), or a root `"$ref"` to
            such a schema in `"$defs"`, optionally wrapped in a single-item `"allOf"`.

    Yields:
        A tuple of `(field_name, field_type, constraints, metadata)` for each property.
            - `field_type`: The property subschema with `$ref`s inlined.
            - `constraints`: Always an empty tuple.
            - `metadata`: The `anyschema`/`x-anyschema` namespaces of the property, plus its `description`.

    Raises:
        ValueError: If `spec` is not a JSON Schema object, or a `$ref` is not local or cannot be resolved.
        UnsupportedDTypeError: If a `$ref` is recursive.

    Examples:
        >>> schema = {
        ...     "type": "object",
        ...     "properties": {
        ...         "id": {"type": "integer"},
        ...         "name": {"type": "string", "description": "Full name"},
        ...         "address": {"$ref": "#/$defs/Address"},
        ...     },
        ...     "$defs": {"Address": {"type": "object", "properties": {"city": {"type": "string"}}}},
        ... }
        >>> for spec_field in jsonschema_adapter(schema):
        ...     print(spec_field)
        ('id', {'type': 'integer'}, (), {})
        ('name', {'type': 'string', 'description': 'Full name'}, (), {'anyschema': {'description': 'Full name'}})
        ('address', {'type': 'object', 'properties': {'city': {'type': 'string'}}}, (), {})
    """
    msg = "Expected a JSON Schema object with a `'properties'` mapping and `'type': 'object'` (or no `'type'`)."
    if not is_jsonschema(spec):
        raise ValueError(msg)
    inlined_spec = inline_refs(spec, spec)
    all_of = inlined_spec.get("allOf")
    if "properties" not in inlined_spec and isinstance(all_of, list) and len(all_of) == 1:
        # Pydantic < 2.9 wraps the root `$ref` of a self-referencing model in a single-item `allOf`.
        inlined_spec = all_of[0] if isinstance(all_of[0], Mapping) else {}
    if not isinstance(properties := inlined_spec.get("properties"), Mapping):  # a root `$ref` to a non-object
        raise ValueError(msg)  # noqa: TRY004
    for field_name, field_schema in properties.items():
        metadata = extract_field_metadata(field_schema)
        # An explicit `nullable` survives a `dtype` override, which skips `JsonSchemaStep`.
        if allows_null(field_schema) and get_anyschema_value_by_key(metadata, key="nullable") is None:
            set_anyschema_meta(metadata, key="nullable", value=True)
        yield field_name, field_schema, (), metadata


def into_ordered_dict_adapter(spec: IntoOrderedDict) -> FieldSpecIterable:
    """Adapter for Python mappings and sequences of field definitions.

    Converts a mapping (e.g., `dict`) or sequence of 2-tuples into an iterator yielding field information as
    `(field_name, field_type, constraints, metadata)` tuples.

    Arguments:
        spec: A mapping from field names to types, or a sequence of `(name, type)` tuples.

    Yields:
        A tuple of `(field_name, field_type, constraints, metadata)` for each field.
        Both constraints and metadata are always empty for this adapter.

    Raises:
        ValueError: If a sequence spec repeats a field name.

    Examples:
        >>> list(into_ordered_dict_adapter({"name": str, "age": int}))
        [('name', <class 'str'>, (), {}), ('age', <class 'int'>, (), {})]

        >>> list(into_ordered_dict_adapter([("age", int), ("name", str)]))
        [('age', <class 'int'>, (), {}), ('name', <class 'str'>, (), {})]
    """
    name_to_type = dict(spec)
    if not isinstance(spec, Mapping) and len(name_to_type) < len(spec):
        counts = Counter(name for name, _ in spec)
        duplicates = ", ".join(f"'{name}'" for name, count in counts.items() if count > 1)
        msg = f"Duplicate field names in spec: {duplicates}."
        raise ValueError(msg)
    for field_name, field_type in name_to_type.items():
        yield field_name, field_type, (), {}


def _ensure_annotations_are_fields(
    spec: type, type_hints: Mapping[str, Any], field_names: Container[str], *, kind: str, fix: str
) -> None:
    """Raise `TypeError` if `spec` has non-`ClassVar` annotations that are not fields.

    This happens when a subclass of a dataclass or attrs class is not decorated itself.
    """
    if non_field_names := [
        name
        for name, tp in type_hints.items()
        if name not in field_names and not (tp is ClassVar or get_origin(tp) is ClassVar)
    ]:
        names = ", ".join(f"'{name}'" for name in non_field_names)
        msg = f"Class '{spec.__name__}' has annotations ({names}) that are not {kind} fields. {fix}"
        raise TypeError(msg)


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
    type_hints = get_type_hints(spec, include_extras=True)
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
    # Evaluates string annotations and forward references up front.
    type_hints = get_type_hints(spec, include_extras=True)
    # `__dataclass_fields__` also holds the `ClassVar` and `InitVar` pseudo-fields, bare or subscripted.
    _ensure_annotations_are_fields(
        spec,
        type_hints,
        spec.__dataclass_fields__,
        kind="dataclass",
        fix="If this class inherits from a dataclass, you must also decorate it with @dataclass "
        "to properly define these fields.",
    )

    for field in dc_fields(spec):
        # Copy, so callers cannot mutate the dataclass field metadata.
        metadata = dict(field.metadata) if field.metadata else {}

        # `Field.doc` exists on Python 3.14+.
        if (doc := getattr(field, "doc", None)) and (get_anyschema_value_by_key(metadata, key="description") is None):
            set_anyschema_meta(metadata, key="description", value=doc)

        yield field.name, type_hints[field.name], (), metadata


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
        ('name', <class 'str'>, (), {'anyschema': {'description': 'Student name'}})
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
        if (description := field_info.description) is not None and (
            get_anyschema_value_by_key(metadata, key="description") is None
        ):
            set_anyschema_meta(metadata, key="description", value=description)

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

    # Evaluates string annotations and forward references up front.
    type_hints = get_type_hints(spec, include_extras=True)
    attrs_fields = attrs.fields(spec)
    _ensure_annotations_are_fields(
        spec,
        type_hints,
        {field.name for field in attrs_fields},
        kind="attrs",
        fix="If this class inherits from an attrs class, you must also decorate it with @attrs.define "
        "or @attrs.frozen to properly define these fields.",
    )

    for field in attrs_fields:
        # Copy, so callers cannot mutate the attrs field metadata.
        metadata = dict(field.metadata) if field.metadata else {}
        yield field.name, type_hints.get(field.name, field.type), (), metadata


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
        ('id', Integer(), (), {'anyschema': {'nullable': False}})
        >>> spec_fields[1]
        ('name', String(length=50), (), {'anyschema': {'nullable': True}})

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
        ('id', Integer(), (), {'anyschema': {'nullable': False}})
        >>> spec_fields[1]  # doctest: +SKIP
        ('name', String(length=50), (), {'anyschema': {'nullable': True}})
    """
    from sqlalchemy import Table

    table = spec if isinstance(spec, Table) else spec.__table__

    meta_mapping: dict[Literal["nullable", "unique", "description"], Literal["nullable", "unique", "doc"]] = {
        "nullable": "nullable",
        "unique": "unique",
        "description": "doc",
    }

    for column in table.columns:
        # Create a copy of column.info to avoid mutating the original SQLAlchemy column
        metadata = dict(column.info)

        # Extract anyschema metadata from SQLAlchemy column attributes
        for key, column_attr in meta_mapping.items():
            if (value := getattr(column, column_attr, None)) is not None and (
                get_anyschema_value_by_key(metadata, key=key) is None
            ):
                set_anyschema_meta(metadata, key=key, value=value)

        yield (column.name, column.type, (), metadata)
