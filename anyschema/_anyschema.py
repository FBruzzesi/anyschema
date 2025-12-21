from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

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
from anyschema.parsers import ParserPipeline

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    import pandas as pd
    import polars as pl
    import pyarrow as pa
    from narwhals.dtypes import DType
    from narwhals.typing import DTypeBackend
    from typing_extensions import Self

    from anyschema.typing import Adapter, IntoParserPipeline, Spec


__all__ = ("AnyField", "AnySchema")


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
            Parsing a type specification will flag this as True if:

            - The `anyschema/nullable` metadata key is explicitly set to True, or
            - The type is `Optional[T]` or `T | None` (which automatically sets the metadata)
        unique: Whether all values in this field must be unique. Defaults to False.
            Determined by the `anyschema/unique` metadata key or SQLAlchemy column unique argument.
        description: Human-readable field description.
        metadata: Custom metadata dict containing any metadata that is not under the `anyschema/*` namespace.

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

        Creates a hashable tuple representation.
        `metadata` is a dict and not hashable, we convert it to a sorted tuple of items
        """
        metadata_tuple = tuple(sorted(self.metadata.items()))
        return hash((self.name, self.dtype, self.nullable, self.unique, self.description, metadata_tuple))


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

    Attributes:
        fields: A mapping from field names to [`AnyField`][anyschema.AnyField] objects,
            containing the parsed dtype and field-level metadata (nullable, unique, etc.).

    Raises:
        ValueError: If `spec` type is unknown and `adapter` is not specified.
        NotImplementedError: If a type in the spec cannot be parsed by any parser in the pipeline.
        UnsupportedDTypeError: If a type is explicitly unsupported (e.g., Union with mixed types).

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

    _nw_schema: Schema
    fields: dict[str, AnyField]

    def __init__(
        self: Self,
        spec: Spec,
        pipeline: ParserPipeline | IntoParserPipeline = "auto",
        adapter: Adapter | None = None,
    ) -> None:
        if isinstance(spec, Schema):
            # Create Field objects from the schema with default values as Narwhals Schema's/Dtypes do not carry
            # nullability, uniqueness nor metadata information.
            self.fields = {name: AnyField(name=name, dtype=dtype) for name, dtype in spec.items()}
            self._nw_schema = spec
            return

        parser_pipeline = pipeline if isinstance(pipeline, ParserPipeline) else ParserPipeline(pipeline)
        adapter_f: Adapter

        if is_into_ordered_dict(spec):
            adapter_f = into_ordered_dict_adapter
        elif is_typed_dict(spec):
            adapter_f = typed_dict_adapter
        elif is_dataclass(spec):
            adapter_f = dataclass_adapter
        elif is_pydantic_base_model(spec):
            adapter_f = pydantic_adapter
        elif is_attrs_class(spec):
            adapter_f = attrs_adapter
        elif is_sqlalchemy_table(spec):
            adapter_f = sqlalchemy_adapter
        elif adapter is not None:
            adapter_f = adapter
        else:
            msg = "`spec` type is unknown and `adapter` is not specified."
            raise ValueError(msg)

        self.fields = {
            name: parser_pipeline.parse_into_field(name, input_type, constraints, metadata)
            for name, input_type, constraints, metadata in adapter_f(cast("Any", spec))
        }
        self._nw_schema = Schema({name: field.dtype for name, field in self.fields.items()})

    def to_arrow(self: Self) -> pa.Schema:
        """Converts input model into pyarrow schema.

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

        return pa.schema(
            pa_field.with_nullable(field.nullable).with_metadata({k: str(v) for k, v in field.metadata.items()})
            if field.metadata
            else pa_field.with_nullable(field.nullable)
            for pa_field, field in zip(self._nw_schema.to_arrow(), self.fields.values(), strict=True)
        )

    def to_pandas(
        self: Self, *, dtype_backend: DTypeBackend | Iterable[DTypeBackend] = None
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
        return self._nw_schema.to_pandas(dtype_backend=dtype_backend)

    def to_polars(self: Self) -> pl.Schema:
        """Converts input model into polars Schema.

        Returns:
            The converted polars schema.

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
        return self._nw_schema.to_polars()
