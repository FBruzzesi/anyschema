from __future__ import annotations

from dataclasses import dataclass, field
from operator import attrgetter
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final, Literal, TypeAlias, TypeVar, cast, overload

import narwhals as nw
from narwhals.schema import Schema

from anyschema._dependencies import (
    is_attrs_class,
    is_dataclass,
    is_into_ordered_dict,
    is_pydantic_base_model,
    is_sqlalchemy_table,
    is_typed_dict,
)
from anyschema.adapters import (
    attrs_adapter,
    dataclass_adapter,
    into_ordered_dict_adapter,
    pydantic_adapter,
    sqlalchemy_adapter,
    typed_dict_adapter,
)
from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers import ParserPipeline
from anyschema.parsers._pipeline import shared_auto_pipeline

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Mapping

    import pandas as pd
    import polars as pl
    import pyarrow as pa
    from duckdb.sqltypes import DuckDBPyType
    from ibis import Schema as IbisSchema
    from ibis.expr.datatypes import DataType as IbisDataType
    from narwhals.dtypes import DType
    from narwhals.typing import DTypeBackend, IntoDType
    from pyspark.sql.types import StructType as PySparkStructType

    from anyschema.typing import Adapter, IntoParserPipeline, Spec

    T = TypeVar("T")
    AnyFieldAttrAccessor: TypeAlias = Callable[["AnyField"], T]

__all__ = ("AnyField", "AnySchema")

_get_description: AnyFieldAttrAccessor[str | None] = attrgetter("description")
_get_dtype: AnyFieldAttrAccessor[DType] = attrgetter("dtype")
_get_nullable: AnyFieldAttrAccessor[bool] = attrgetter("nullable")
_get_unique: AnyFieldAttrAccessor[bool] = attrgetter("unique")


def _enums_to_categorical(dtype: IntoDType) -> IntoDType:
    """Return `dtype` with every nested `Enum` replaced by `Categorical`."""
    if isinstance(dtype, nw.Enum):
        return nw.Categorical()
    if isinstance(dtype, nw.List):
        return nw.List(_enums_to_categorical(dtype.inner))
    if isinstance(dtype, nw.Array):
        return nw.Array(_enums_to_categorical(dtype.inner), dtype.size)
    if isinstance(dtype, nw.Struct):
        return nw.Struct([nw.Field(field.name, _enums_to_categorical(field.dtype)) for field in dtype.fields])
    if isinstance(dtype, nw.Map):
        return nw.Map(_enums_to_categorical(dtype.key), _enums_to_categorical(dtype.value))
    return dtype


def _infer_adapter(spec: Spec) -> Adapter:
    """Return the built-in adapter for the type of `spec`.

    Raises:
        ValueError: If no built-in adapter supports `spec`.
    """
    if is_into_ordered_dict(spec):
        return into_ordered_dict_adapter
    if is_typed_dict(spec):
        return typed_dict_adapter
    if is_dataclass(spec):
        return dataclass_adapter
    if is_pydantic_base_model(spec):
        return pydantic_adapter
    if is_attrs_class(spec):
        return attrs_adapter
    if is_sqlalchemy_table(spec):
        return sqlalchemy_adapter
    msg = "`spec` type is unknown and `adapter` is not specified."
    raise ValueError(msg)


def _iter_dtypes(dtype: IntoDType) -> Iterator[IntoDType]:
    """Yield `dtype` and every dtype nested in it, depth first."""
    yield dtype
    if isinstance(dtype, (nw.List, nw.Array)):
        yield from _iter_dtypes(dtype.inner)
    elif isinstance(dtype, nw.Struct):
        for field in dtype.fields:
            yield from _iter_dtypes(field.dtype)
    elif isinstance(dtype, nw.Map):
        yield from _iter_dtypes(dtype.key)
        yield from _iter_dtypes(dtype.value)


POLARS_HAS_INT_128: Final[tuple[int, ...]] = (1, 18, 0)
"""https://github.com/pola-rs/polars/pull/20232"""

POLARS_HAS_UINT_128: Final[tuple[int, ...]] = (1, 34, 0)
"""https://github.com/pola-rs/polars/pull/24346"""

POLARS_HAS_FLOAT_16: Final[tuple[int, ...]] = (1, 36, 0)
"""https://github.com/pola-rs/polars/pull/25185"""

POLARS_HAS_MAP: Final[tuple[int, ...]] = (2, 0, 0)
"""https://github.com/pola-rs/polars/pull/28984"""

# Below these versions narwhals gives `pl.Unknown` for the dtype (or raises its own error for `Map`).
_POLARS_MIN_VERSION_BY_DTYPE: Final[Mapping[type[DType], tuple[int, ...]]] = {
    nw.Int128: POLARS_HAS_INT_128,
    nw.UInt128: POLARS_HAS_UINT_128,
    nw.Float16: POLARS_HAS_FLOAT_16,
    nw.Map: POLARS_HAS_MAP,
}


def _is_tz_aware_datetime(dtype: IntoDType) -> bool:
    return isinstance(dtype, nw.Datetime) and dtype.time_zone is not None


@dataclass(frozen=True, slots=True, kw_only=True)
class AnyField:
    """A structured field descriptor.

    Arguments:
        name: The name of the field.
        dtype: The Narwhals data type.
        nullable: Whether the field accepts null values.
        unique: Whether values must be unique.
        description: Optional field description.
        metadata: Custom metadata dictionary.

    Attributes:
        name: The name of the field.
        dtype: The Narwhals data type of the field.
        nullable: Whether the field can contain null values. Defaults to False.
            When parsing a spec, the `{"anyschema": {"nullable": ...}}` metadata key wins if set. Otherwise the field
            is nullable if its field-level type contains `None` (e.g. `T | None`, but not `list[T | None]`), whether
            or not `dtype` is overridden.
        unique: Whether all values in this field must be unique. Defaults to False.
            Determined by the `{"anyschema": {"unique": ...}}` metadata key or SQLAlchemy column unique argument.
        description: Human-readable field description.
        metadata: Custom metadata dict containing any metadata that is not under the `anyschema` or `x-anyschema`
            namespace.

    Examples:
        Creating a simple field:

        >>> import narwhals as nw
        >>> from anyschema import AnyField
        >>>
        >>> field = AnyField(
        ...     name="user_id",
        ...     dtype=nw.Int64(),
        ...     nullable=False,
        ...     unique=True,
        ...     description="Primary key",
        ... )
        >>> field
        AnyField(name='user_id', dtype=Int64, nullable=False, unique=True, description='Primary key', metadata={})

        AnyField with optional type:

        >>> field = AnyField(
        ...     name="email",
        ...     dtype=nw.String(),
        ...     nullable=True,
        ...     unique=False,
        ...     metadata={"fmt": "email"},
        ... )
        >>> field
        AnyField(name='email', dtype=String, nullable=True, unique=False, description=None, metadata={'fmt': 'email'})
    """

    name: str
    dtype: DType
    nullable: bool = False
    unique: bool = False
    description: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Return hash of the instance.

        Leaves out `metadata`, whose values can be unhashable (lists, dicts). Equal fields still hash equal
        because `__eq__` compares every hashed attribute.
        """
        return hash((self.name, self.dtype, self.nullable, self.unique, self.description))


class AnySchema:
    """The class implements the workflow to convert from a (schema) specification to a native dataframe schema object.

    The `AnySchema` class enables to convert from type specifications (such as Pydantic models) to native dataframe
    schemas (such as `pandas`, `polars` and `pyarrow`).

    This class provides a unified interface for generating dataframe schemas from various input formats,
    with extensible type parsing through a modular pipeline architecture.

    Arguments:
        spec: The input specification. This can be:

            - A [Narwhals Schema](https://narwhals-dev.github.io/narwhals/api-reference/schema/#narwhals.schema.Schema).
                In this case parsing data types is a no-op and the schema is used directly.
            - A python [mapping](https://docs.python.org/3/glossary.html#term-mapping) (like `dict`) or
                [sequence](https://docs.python.org/3/glossary.html#term-sequence) of tuples containing
                the field name and type (e.g., `{"name": str, "age": int}` or `[("name", str), ("age", int)]`).
            - A [TypedDict](https://docs.python.org/3/library/typing.html#typing.TypedDict) class (not an instance).
                The fields are extracted using type hint introspection.
            - A [dataclass](https://docs.python.org/3/library/dataclasses.html) class (not an instance).
                The fields are extracted using dataclass introspection.
            - A [Pydantic Model](https://docs.pydantic.dev/latest/concepts/models/) class (not an instance).
                The fields are extracted using Pydantic's schema introspection.
            - An [attrs class](https://www.attrs.org/) (not an instance).
                The fields are extracted using attrs introspection.
            - A [SQLAlchemy Table](https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.Table)
                instance or [DeclarativeBase](https://docs.sqlalchemy.org/en/20/orm/mapping_api.html#sqlalchemy.orm.DeclarativeBase)
                subclass (not an instance).
                The fields are extracted using SQLAlchemy's schema introspection.

        pipeline: Control how types are parsed into Narwhals dtypes. Options:

            - `"auto"` (default): Automatically select the appropriate parser steps based on the installed dependencies.
            - A [`ParserPipeline`][anyschema.parsers.ParserPipeline] instance: Use this pipeline directly.
            - A sequence of [`ParserStep`][anyschema.parsers.ParserStep] instances to build a pipeline.

                **Warning**: Order matters! More specific parsers should come before general ones.

            This allows for custom type parsing logic and extensibility through user-defined parser steps.

        adapter: A custom adapter callable that converts the spec into a sequence of field specifications.
            The callable should yield tuples of `(name, type, constraints, metadata)` for each field in the spec.

            - `name` (str): The name of the field
            - `type/annotation` (type): The type annotation of the field
            - `constraints` (tuple): Constraints associated with the field
                (e.g., `Gt`, `Le` constraints from `annotated-types`).
            - `metadata` (dict): Custom metadata dictionary.
                (e.g., from `json_schema_extra` in Pydantic Field's, `metadata` in attrs and dataclasses field's)

            This allows for custom field specification logic and extensibility from user-defined adapters.
            When given, it is used for every spec, including types anyschema recognizes.

    Attributes:
        fields: A mapping from field names to [`AnyField`][anyschema.AnyField] objects,
            containing the parsed dtype and field-level metadata (nullable, unique, etc.).

    Raises:
        ValueError: If `spec` type is unknown and `adapter` is not specified.
        NotImplementedError: If a type in the spec cannot be parsed by any parser in the pipeline.
        UnsupportedDTypeError: If a type is explicitly unsupported (e.g., Union with mixed types) or recursive.

    Examples:
        Basic usage with a Pydantic model:

        >>> from anyschema import AnySchema
        >>> from pydantic import BaseModel, PositiveInt
        >>>
        >>> class Student(BaseModel):
        ...     name: str
        ...     age: PositiveInt
        ...     classes: list[str] | None
        >>>
        >>> schema = AnySchema(spec=Student)

        Convert to PyArrow schema:

        >>> pa_schema = schema.to_arrow()
        >>> print(pa_schema)
        name: string not null
        age: uint64 not null
        classes: list<item: string>
          child 0, item: string

        Convert to Polars schema:

        >>> pl_schema = schema.to_polars()
        >>> print(pl_schema)
        Schema({'name': String, 'age': UInt64, 'classes': List(String)})

        Convert to Pandas schema:

        >>> pd_schema = schema.to_pandas()
        >>> print(pd_schema)
        {'name': <class 'str'>, 'age': 'uint64', 'classes': list<item: string>[pyarrow]}

        Using a plain Python dict:

        >>> schema = AnySchema(spec={"id": int, "name": str, "active": bool})
        >>> print(schema.to_arrow())
        id: int64 not null
        name: string not null
        active: bool not null

        Using a TypedDict:

        >>> from typing_extensions import TypedDict
        >>>
        >>> class Product(TypedDict):
        ...     id: int
        ...     name: str
        ...     price: float | None
        >>>
        >>> schema = AnySchema(spec=Product)
        >>> print(schema.to_arrow())
        id: int64 not null
        name: string not null
        price: double

    Tip: See also
        - [ParserStep][anyschema.parsers.ParserStep]: Base class for custom parser steps
        - [ParserPipeline][anyschema.parsers.ParserPipeline]: Pipeline for chaining parser steps
        - [Spec Adapters][anyschema.adapters]: Adapters for various specifications
    """

    __slots__ = ("_fields", "_nw_schema")

    _nw_schema: Schema
    _fields: MappingProxyType[str, AnyField]

    def __init__(
        self,
        spec: Spec,
        pipeline: ParserPipeline | IntoParserPipeline = "auto",
        adapter: Adapter | None = None,
    ) -> None:
        if isinstance(spec, Schema):
            # Create Field objects from the schema with default values as Narwhals Schema's/Dtypes do not carry
            # nullability, uniqueness nor metadata information.
            self._fields = MappingProxyType({name: AnyField(name=name, dtype=dtype) for name, dtype in spec.items()})
            self._nw_schema = spec
            return

        if isinstance(pipeline, ParserPipeline):
            parser_pipeline = pipeline
        elif pipeline == "auto":
            parser_pipeline = shared_auto_pipeline()
        else:
            parser_pipeline = ParserPipeline(pipeline)
        spec_adapter = adapter if adapter is not None else _infer_adapter(spec)

        self._fields = MappingProxyType(
            {
                name: parser_pipeline.parse_into_field(name, input_type, constraints, metadata)
                for name, input_type, constraints, metadata in spec_adapter(cast("Any", spec))
            }
        )
        self._nw_schema = Schema({name: field.dtype for name, field in self._fields.items()})

    def names(self) -> tuple[str, ...]:
        """Return the names of all fields in the schema.

        Returns:
            Tuple of field names in the order they appear in the schema.

        Examples:
            >>> from anyschema import AnySchema
            >>>
            >>> schema = AnySchema(spec={"id": int, "name": str, "age": int})
            >>> schema.names()
            ('id', 'name', 'age')
        """
        return tuple(self._fields.keys())

    def field(self, name: str) -> AnyField:
        """Get a specific field by name.

        Arguments:
            name: The name of the field to retrieve.

        Returns:
            The AnyField object for the specified field name.

        Raises:
            KeyError: If the field name does not exist in the schema.

        Examples:
            >>> from anyschema import AnySchema
            >>>
            >>> schema = AnySchema(spec={"id": int, "name": str})
            >>> field = schema.field("name")
            >>> field.dtype
            String
            >>> field.nullable
            False
        """
        return self._fields[name]

    @property
    def fields(self) -> dict[str, AnyField]:
        """Get all fields as a dictionary.

        Returns:
            Dictionary mapping field names to AnyField objects.

        Examples:
            >>> from anyschema import AnySchema
            >>>
            >>> schema = AnySchema(spec={"id": int, "name": str})
            >>> fields = schema.fields
            >>> fields["name"].dtype
            String
            >>> list(fields.keys())
            ['id', 'name']
        """
        return dict(self._fields)

    def _get_field_attribute(
        self, attr_getter: AnyFieldAttrAccessor[T], *, named: bool
    ) -> dict[str, T] | tuple[T, ...]:
        """Extract an attribute from all fields, returning either a dict or tuple.

        Arguments:
            attr_getter: Function that extracts the desired attribute from an AnyField.
            named: If True, return a dict mapping field names to values. If False, return a tuple of values.

        Returns:
            Either a dict mapping field names to attribute values, or a tuple of attribute values.
        """
        return (
            {_field.name: attr_getter(_field) for _field in self._fields.values()}
            if named
            else tuple(attr_getter(_field) for _field in self._fields.values())
        )

    @overload
    def dtypes(self, *, named: Literal[True]) -> dict[str, DType]: ...

    @overload
    def dtypes(self, *, named: Literal[False] = False) -> tuple[DType, ...]: ...

    def dtypes(self, *, named: bool = False) -> dict[str, DType] | tuple[DType, ...]:
        """Get the data types of all fields.

        Arguments:
            named: If True, return a dict mapping field names to dtypes.
                If False (default), return a tuple of dtypes in field order.

        Returns:
            Either a dict of {field_name: dtype} or a tuple of dtypes.

        Examples:
            >>> from anyschema import AnySchema
            >>>
            >>> schema = AnySchema(spec={"id": int, "name": str, "score": float})
            >>> schema.dtypes()
            (Int64, String, Float64)
            >>> schema.dtypes(named=True)
            {'id': Int64, 'name': String, 'score': Float64}
        """
        return self._get_field_attribute(_get_dtype, named=named)

    @overload
    def descriptions(self, *, named: Literal[True]) -> dict[str, str | None]: ...

    @overload
    def descriptions(self, *, named: Literal[False] = False) -> tuple[str | None, ...]: ...

    def descriptions(self, *, named: bool = False) -> dict[str, str | None] | tuple[str | None, ...]:
        """Get the descriptions of all fields.

        Arguments:
            named: If True, return a dict mapping field names to descriptions.
                If False (default), return a tuple of descriptions in field order.

        Returns:
            Either a dict of {field_name: description} or a tuple of descriptions.
                Description values are None for fields without descriptions.

        Examples:
            >>> from anyschema import AnySchema
            >>> from pydantic import BaseModel, Field
            >>>
            >>> class User(BaseModel):
            ...     id: int = Field(description="User ID")
            ...     name: str
            >>>
            >>> schema = AnySchema(spec=User)
            >>> schema.descriptions()
            ('User ID', None)
            >>> schema.descriptions(named=True)
            {'id': 'User ID', 'name': None}
        """
        return self._get_field_attribute(_get_description, named=named)

    @overload
    def nullables(self, *, named: Literal[True]) -> dict[str, bool]: ...

    @overload
    def nullables(self, *, named: Literal[False] = False) -> tuple[bool, ...]: ...

    def nullables(self, *, named: bool = False) -> dict[str, bool] | tuple[bool, ...]:
        """Get the nullable flags of all fields.

        Arguments:
            named: If True, return a dict mapping field names to nullable flags.
                If False (default), return a tuple of nullable flags in field order.

        Returns:
            Either a dict of {field_name: nullable} or a tuple of nullable flags. A field is nullable if it accepts
                None values (e.g., `Optional[int]` or `int | None`).

        Examples:
            >>> from anyschema import AnySchema
            >>>
            >>> schema = AnySchema(spec={"id": int, "name": str, "age": int | None})
            >>> schema.nullables()
            (False, False, True)
            >>> schema.nullables(named=True)
            {'id': False, 'name': False, 'age': True}
        """
        return self._get_field_attribute(_get_nullable, named=named)

    @overload
    def uniques(self, *, named: Literal[True]) -> dict[str, bool]: ...

    @overload
    def uniques(self, *, named: Literal[False] = False) -> tuple[bool, ...]: ...

    def uniques(self, *, named: bool = False) -> dict[str, bool] | tuple[bool, ...]:
        """Get the unique constraint flags of all fields.

        Arguments:
            named: If True, return a dict mapping field names to unique flags.
                If False (default), return a tuple of unique flags in field order.

        Returns:
            Either a dict of {field_name: unique} or a tuple of unique flags. A field is unique if it has a uniqueness
                constraint (e.g., from SQLAlchemy or metadata).

        Examples:
            >>> from anyschema import AnySchema
            >>> from sqlalchemy import Column, Integer, String, Table, MetaData
            >>>
            >>> users_table = Table(
            ...     "users",
            ...     MetaData(),
            ...     Column("id", Integer, primary_key=True),
            ...     Column("email", String, unique=True),
            ...     Column("name", String),
            ... )
            >>>
            >>> schema = AnySchema(spec=users_table)
            >>> schema.uniques()
            (False, True, False)
            >>> schema.uniques(named=True)
            {'id': False, 'email': True, 'name': False}
        """
        return self._get_field_attribute(_get_unique, named=named)

    def __eq__(self, other: object) -> bool:
        """Check equality between two AnySchema instances.

        Two AnySchema instances are considered equal if they have the same fields.

        Arguments:
            other: Object to compare with.

        Returns:
            True if both instances have identical fields, False otherwise.

        Examples:
            >>> from anyschema import AnySchema
            >>>
            >>> schema1 = AnySchema(spec={"name": str, "age": int})
            >>> schema2 = AnySchema(spec={"name": str, "age": int})
            >>> schema3 = AnySchema(spec={"name": str})
            >>>
            >>> schema1 == schema2
            True
            >>> schema1 == schema3
            False
        """
        return isinstance(other, AnySchema) and tuple(self._fields.values()) == tuple(other._fields.values())

    def __hash__(self) -> int:
        """Compute hash value for the AnySchema instance.

        This allows AnySchema instances to be used in sets and as dictionary keys.

        Returns:
            Hash value of the schema.

        Examples:
            >>> from anyschema import AnySchema
            >>>
            >>> schema1 = AnySchema(spec={"name": str, "age": int})
            >>> schema2 = AnySchema(spec={"name": str, "age": int})
            >>>
            >>> hash(schema1) == hash(schema2)
            True
            >>> len({schema1, schema2})
            1
        """
        return hash(tuple(self._fields.values()))

    def to_arrow(self) -> pa.Schema:
        """Converts input model into pyarrow schema.

        `Enum` and `Literal` fields, at any nesting level, become dictionary-encoded strings
        (`dictionary<values=string, indices=uint32>`).

        Returns:
            The converted pyarrow schema.

        Examples:
            >>> from anyschema import AnySchema
            >>> from pydantic import BaseModel
            >>>
            >>>
            >>> class User(BaseModel):
            ...     id: int
            ...     username: str
            ...     email: str | None
            ...     is_active: bool
            >>>
            >>> schema = AnySchema(spec=User)
            >>> schema.to_arrow()
            id: int64 not null
            username: string not null
            email: string
            is_active: bool not null
        """
        import pyarrow as pa

        # NOTE: narwhals cannot convert Enum to pyarrow, but converts Categorical to an Arrow dictionary.
        arrow_schema = Schema(
            {name: _enums_to_categorical(dtype) for name, dtype in self._nw_schema.items()}
        ).to_arrow()
        return pa.schema(
            pa_field.with_nullable(field.nullable).with_metadata({k: str(v) for k, v in field.metadata.items()})
            if field.metadata
            else pa_field.with_nullable(field.nullable)
            for pa_field, field in zip(arrow_schema, self._fields.values(), strict=True)
        )

    def to_pandas(
        self, *, dtype_backend: DTypeBackend | Iterable[DTypeBackend] = None
    ) -> dict[str, str | pd.ArrowDtype | type]:
        """Converts input model into mapping of {field_name: pandas_dtype}.

        Arguments:
            dtype_backend: which kind of data type backend to use.

        Returns:
            The converted pandas schema.

        Examples:
            >>> from anyschema import AnySchema
            >>> from pydantic import BaseModel
            >>>
            >>>
            >>> class User(BaseModel):
            ...     id: int
            ...     username: str
            ...     email: str
            ...     is_active: bool
            >>>
            >>> schema = AnySchema(spec=User)
            >>> schema.to_pandas(dtype_backend=("pyarrow", "numpy_nullable", "pyarrow", None))
            {'id': 'Int64[pyarrow]', 'username': 'string', 'email': string[pyarrow], 'is_active': 'bool'}
        """
        # NOTE: narwhals converts a top-level Enum to a pandas Categorical, but cannot convert a nested one.
        nw_schema = Schema(
            {
                name: dtype if isinstance(dtype, nw.Enum) else _enums_to_categorical(dtype)
                for name, dtype in self._nw_schema.items()
            }
        )
        return nw_schema.to_pandas(dtype_backend=dtype_backend)

    def to_polars(self) -> pl.Schema:
        """Converts input model into polars Schema.

        Returns:
            The converted polars schema.

        Raises:
            UnsupportedDTypeError: If a dtype, at any nesting level, is newer than the installed polars: Int128
                needs polars 1.18, UInt128 1.34, Float16 1.36 and Map 2.0.

        Examples:
            >>> from anyschema import AnySchema
            >>> from pydantic import BaseModel
            >>>
            >>>
            >>> class User(BaseModel):
            ...     id: int
            ...     username: str
            ...     email: str
            ...     is_active: bool
            >>>
            >>> schema = AnySchema(spec=User)
            >>> schema.to_polars()
            Schema({'id': Int64, 'username': String, 'email': String, 'is_active': Boolean})
        """
        import polars as pl
        from narwhals.utils import parse_version

        polars_version = parse_version(pl.__version__)
        if too_new := {
            dtype_cls: min_version
            for dtype_cls, min_version in _POLARS_MIN_VERSION_BY_DTYPE.items()
            if polars_version < min_version
        }:
            for name, dtype in self._nw_schema.items():
                for nested in _iter_dtypes(dtype):
                    # `base_type()` also matches class-form children such as `nw.List(nw.Float16)`.
                    if (min_version := too_new.get(nested.base_type())) is not None:
                        msg = (
                            f"{nested.base_type().__name__} needs polars>={'.'.join(map(str, min_version))}, "
                            f"found {pl.__version__} (field '{name}')"
                        )
                        raise UnsupportedDTypeError(msg)
        return self._nw_schema.to_polars()

    def to_duckdb(self) -> dict[str, DuckDBPyType]:
        """Converts input model into mapping of {field_name: duckdb_type}.

        DuckDB types carry no nullability or metadata, so only data types are converted.

        Timezone-aware datetimes become `TIMESTAMPTZ`, which stores an instant and displays it in the connection time
        zone. The original time zone name is dropped.

        Returns:
            The converted duckdb schema.

        Raises:
            UnsupportedDTypeError: If a dtype has no DuckDB equivalent (Categorical, Float16, Object, Unknown), or a
                timezone-aware datetime has a time unit other than microseconds.

        Examples:
            >>> from anyschema import AnySchema
            >>> from pydantic import BaseModel
            >>>
            >>>
            >>> class User(BaseModel):
            ...     id: int
            ...     username: str
            ...     tags: list[str]
            >>>
            >>> schema = AnySchema(spec=User)
            >>> {name: str(dtype) for name, dtype in schema.to_duckdb().items()}
            {'id': 'BIGINT', 'username': 'VARCHAR', 'tags': 'VARCHAR[]'}
        """
        import duckdb
        from narwhals._duckdb.utils import narwhals_to_native_dtype
        from narwhals.utils import Version

        version = Version.MAIN
        dtypes = version.dtypes

        # Nested dtypes are converted here, not by narwhals: narwhals needs a live relation to resolve tz-aware
        # datetimes, quotes enum categories with repr, and reverses the shape of multi-dimensional arrays.
        def to_duckdb_type(dtype: IntoDType) -> DuckDBPyType:
            if isinstance(dtype, dtypes.Datetime) and dtype.time_zone is not None:
                if dtype.time_unit != "us":
                    msg = f"DuckDB supports only microsecond precision for timezone-aware datetimes, found {dtype}"
                    raise UnsupportedDTypeError(msg)
                return duckdb.sqltype("TIMESTAMPTZ")
            if isinstance(dtype, dtypes.Enum):
                categories = ", ".join("'{}'".format(category.replace("'", "''")) for category in dtype.categories)
                return duckdb.sqltype(f"ENUM({categories})")
            if isinstance(dtype, dtypes.List):
                return duckdb.list_type(to_duckdb_type(dtype.inner))
            if isinstance(dtype, dtypes.Array):
                return duckdb.array_type(to_duckdb_type(dtype.inner), dtype.size)
            if isinstance(dtype, dtypes.Struct):
                return duckdb.struct_type({field.name: to_duckdb_type(field.dtype) for field in dtype.fields})
            if isinstance(dtype, dtypes.Map):
                return duckdb.map_type(to_duckdb_type(dtype.key), to_duckdb_type(dtype.value))
            if issubclass(dtype.base_type(), (dtypes.Categorical, dtypes.Float16, dtypes.Object, dtypes.Unknown)):
                msg = f"{dtype} has no DuckDB equivalent"
                raise UnsupportedDTypeError(msg)
            return narwhals_to_native_dtype(dtype, version=version, deferred_time_zone=None)  # type: ignore[arg-type]

        return {field.name: to_duckdb_type(field.dtype) for field in self._fields.values()}

    def to_ibis(self) -> IbisSchema:
        """Converts input model into ibis [Schema](https://ibis-project.org/reference/schemas#ibis.expr.schema.Schema).

        Each field keeps its nullability. Nested element and struct field types are always nullable. Field metadata
        is dropped, because Ibis schemas cannot store it.

        Returns:
            The converted ibis schema.

        Raises:
            UnsupportedDTypeError: If a dtype, at any nesting level, is Int128, UInt128, Categorical, Enum, Object or
                Unknown. Ibis has no equivalent for these.

        Examples:
            >>> from anyschema import AnySchema
            >>> from pydantic import BaseModel
            >>>
            >>>
            >>> class User(BaseModel):
            ...     id: int
            ...     username: str | None
            ...     tags: list[str]
            >>>
            >>> schema = AnySchema(spec=User)
            >>> print(schema.to_ibis())
            ibis.Schema {
              id        !int64
              username  string
              tags      !array<string>
            }
        """
        import ibis
        from narwhals._ibis.utils import narwhals_to_native_dtype
        from narwhals.utils import Version

        version = Version.MAIN

        def to_ibis_type(field: AnyField) -> IbisDataType:
            try:
                ibis_type = narwhals_to_native_dtype(field.dtype, version=version)
            # narwhals raises NotImplementedError for Int128/UInt128/Categorical/Enum, AssertionError for Object/Unknown
            except (NotImplementedError, AssertionError) as exc:
                msg = f"{field.dtype} has no Ibis equivalent (field '{field.name}')"
                raise UnsupportedDTypeError(msg) from exc
            return ibis_type.copy(nullable=field.nullable)

        return ibis.schema({field.name: to_ibis_type(field) for field in self._fields.values()})

    def to_pyspark(self) -> PySparkStructType:
        """Converts input model into pyspark [StructType](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.types.StructType.html).

        Returns:
            The converted pyspark StructType.

        Raises:
            UnsupportedDTypeError: If a dtype, at any nesting level, has no PySpark equivalent (e.g. Float16, Enum,
                Object, unsigned integers).

        Examples:
            >>> from anyschema import AnySchema
            >>> from pydantic import BaseModel
            >>>
            >>>
            >>> class User(BaseModel):
            ...     id: int
            ...     username: str | None
            >>>
            >>> schema = AnySchema(spec=User)
            >>> schema.to_pyspark()
            StructType([StructField('id', LongType(), False), StructField('username', StringType(), True)])
        """
        from narwhals._spark_like.utils import narwhals_to_native_dtype
        from narwhals.exceptions import UnsupportedDTypeError as NarwhalsUnsupportedDTypeError
        from narwhals.utils import Version
        from pyspark.sql import SparkSession, types

        # NOTE: narwhals reads the session only for timezone-aware datetimes, and starting one can boot a JVM.
        needs_session = any(
            _is_tz_aware_datetime(nested) for field in self._fields.values() for nested in _iter_dtypes(field.dtype)
        )
        session = SparkSession.builder.getOrCreate() if needs_session else None
        version = Version.MAIN

        def to_spark_type(field: AnyField) -> types.DataType:
            try:
                spark_type: types.DataType = narwhals_to_native_dtype(
                    field.dtype, version=version, spark_types=types, session=session
                )
            # narwhals raises its own UnsupportedDTypeError for Float16/Enum/..., AssertionError for Object/Unknown
            except (NarwhalsUnsupportedDTypeError, AssertionError) as exc:
                msg = f"{field.dtype} has no PySpark equivalent (field '{field.name}')"
                raise UnsupportedDTypeError(msg) from exc
            return spark_type

        return types.StructType(
            fields=[
                types.StructField(
                    name=field.name,
                    dataType=to_spark_type(field),
                    nullable=field.nullable,
                    metadata=dict(field.metadata),
                )
                for field in self._fields.values()
            ]
        )
