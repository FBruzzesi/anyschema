from __future__ import annotations

from collections.abc import Callable, Generator, Mapping, Sequence
from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol, TypeAlias, TypedDict

if TYPE_CHECKING:
    from dataclasses import Field as DataclassField
    from typing import ClassVar

    from attrs import AttrsInstance
    from marshmallow import Schema as MarshmallowSchema
    from marshmallow.fields import Field as MarshmallowField
    from narwhals.dtypes import DType
    from narwhals.schema import Schema as NarwhalsSchema
    from narwhals.typing import TimeUnit
    from pydantic import BaseModel
    from sqlalchemy import Table
    from sqlalchemy.orm import DeclarativeBase
    from sqlalchemy.sql.type_api import TypeEngine

    from anyschema.parsers import ParserStep

    AttrsClassType: TypeAlias = type[AttrsInstance]
    MarshmallowSchemaType: TypeAlias = type[MarshmallowSchema]
    PydanticBaseModelType: TypeAlias = type[BaseModel]
    SQLAlchemyTableType: TypeAlias = Table | type[DeclarativeBase]


IntoOrderedDict: TypeAlias = Mapping[str, type] | Sequence[tuple[str, type]]
"""An object that can be converted into a python [`OrderedDict`][ordered-dict].

We check for the object to be either a mapping or a sequence of sized 2 tuples.

[ordered-dict]: https://docs.python.org/3/library/collections.html#collections.OrderedDict
"""

IntoParserPipeline: TypeAlias = "Literal['auto'] | Sequence['ParserStep']"
"""An object that can be converted into a [`ParserPipeline`][anyschema.parsers.ParserPipeline].

Either "auto" or a sequence of [`ParserStep`][anyschema.parsers.ParserStep].
"""

UnknownSpec: TypeAlias = Any
"""An unknown specification."""

Spec: TypeAlias = "NarwhalsSchema | IntoOrderedDict | PydanticBaseModelType | DataclassType | TypedDictType | AttrsClassType | SQLAlchemyTableType | MarshmallowSchemaType | UnknownSpec"  # noqa: E501
"""Input specification supported directly by [`AnySchema`][anyschema.AnySchema]."""

FieldName: TypeAlias = str
FieldType: TypeAlias = "type[Any] | Annotated[Any, ...] | TypeEngine[Any] | MarshmallowField[Any]"
FieldConstraints: TypeAlias = tuple[Any, ...]
FieldMetadata: TypeAlias = dict[str, Any]

FieldSpec: TypeAlias = tuple[FieldName, FieldType, FieldConstraints, FieldMetadata]
"""Field specification: alias for a tuple of `(str, type, tuple(constraints, ...), dict(metadata))`."""

FieldSpecIterable: TypeAlias = Generator[FieldSpec, None, None]
"""Return type of an adapter."""

Adapter: TypeAlias = Callable[[Any], FieldSpecIterable]
"""Adapter expected signature.

An adapter is a callable that adapts a spec into field specifications.
"""


class DataclassInstance(Protocol):
    """Protocol that represents a dataclass in Python."""

    # dataclasses are runtime composed entities making them tricky to type, this may not work perfectly
    #   with all type checkers
    # code adapted from typeshed:
    # https://github.com/python/typeshed/blob/9ab7fde0a0cd24ed7a72837fcb21093b811b80d8/stdlib/_typeshed/__init__.pyi#L351
    __dataclass_fields__: ClassVar[dict[str, DataclassField[Any]]]


DataclassType = type[DataclassInstance]


class TypedDictType(Protocol):
    """Protocol that represents a TypedDict in Python."""

    __annotations__: dict[str, type]
    __required_keys__: frozenset[str]
    __optional_keys__: frozenset[str]


class AnySchemaMetadata(TypedDict, total=False):
    """TypedDict for anyschema-specific metadata keys.

    This structure defines the nested metadata format that anyschema recognizes
    for controlling field parsing behavior. All keys are optional.

    Attributes:
        description: Human-readable description of the field.
        dtype: Narwhals DType (or its serialized/string representation)
        nullable: Whether the field can contain null values.
        time_zone: Timezone for datetime fields (e.g., "UTC", "Europe/Berlin").
        time_unit: Time precision for datetime fields ("s", "ms", "us", "ns").
        unique: Whether all values in the field must be unique.

    Examples:
        >>> metadata: AnySchemaMetadata = {"nullable": True, "time_zone": "UTC"}
        >>> metadata["unique"] = False
    """

    description: str | None
    dtype: str | DType
    nullable: bool
    time_zone: str
    time_unit: TimeUnit
    unique: bool


AnySchemaMetadataKey: TypeAlias = Literal["description", "dtype", "nullable", "time_zone", "time_unit", "unique"]
AnySchemaNamespaceKey: TypeAlias = Literal["anyschema", "x-anyschema"]
