from __future__ import annotations

from collections import OrderedDict
from dataclasses import fields as dc_fields
from typing import TYPE_CHECKING

from typing_extensions import get_type_hints

if TYPE_CHECKING:
    from pydantic import BaseModel

    from anyschema.typing import DataclassType, FieldSpecIterable, IntoOrderedDict, TypedDictType

__all__ = ("dataclass_adapter", "into_ordered_dict_adapter", "pydantic_adapter", "typed_dict_adapter")


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
    for field in dc_fields(spec):
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
