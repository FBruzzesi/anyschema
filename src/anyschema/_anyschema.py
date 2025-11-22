from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING

from narwhals.schema import Schema

from anyschema._dependencies import is_pydantic_base_model
from anyschema.parsers import create_parser_chain

if TYPE_CHECKING:
    from collections.abc import Iterable

    import pandas as pd
    import polars as pl
    import pyarrow as pa
    from narwhals.typing import DTypeBackend
    from pydantic import BaseModel
    from typing_extensions import Self

    from anyschema.typing import IntoOrderedDict, IntoParserChain


class AnySchema:
    """A utility class for converting from a model-like to a native dataframe schema object.

    The `AnySchema` class bridges the gap between Narwhals' Schemas and Pydantic Models, and popular dataframe libraries
    such as `pandas`, `polars` and `pyarrow`, by enabling converting from the former to latter native schemas.

    This class takes a Pydantic `BaseModel` or its subclass as input and provides methods to generate
    equivalent dataframe schemas.

    Arguments:
        model: The input model. This can be:

            - a [Narwhals Schema](https://narwhals-dev.github.io/narwhals/api-reference/schema/#narwhals.schema.Schema).
                In this case parsing data types is a no-op.
            - a [python mapping](https://docs.python.org/3/glossary.html#term-mapping).
            - a [Pydantic Model](https://docs.pydantic.dev/latest/concepts/models/) class or an instance of such

        parsers: Control how types are parsed into Narwhals dtypes. Options:

            - `"auto"` (default): Automatically select appropriate parsers based on the model type
            - A sequence of parser instances: Use custom parsers for extensibility

            This allows for custom type parsing logic and extensibility from user-defined parsers.

    Raises:
        NotImplementedError:
            If `model` is not a narwhals Schema or a Pydantic model.

    Examples:
        >>> from anyschema import AnySchema
        >>> from pydantic import BaseModel
        >>> from pydantic import PositiveInt
        >>>
        >>> class Student(BaseModel):
        ...     name: str
        ...     age: PositiveInt
        ...     classes: list[str]
        >>>
        >>> schema = AnySchema(schema=Student)

        We can now convert `schema` to a pyarrow schema via `to_arrow` method:

        >>> pa_schema = schema.to_arrow()
        >>> type(pa_schema)
        <class 'pyarrow.lib.Schema'>

        >>> pa_schema
        name: string
        age: uint64
        classes: list<item: string>
          child 0, item: string

        Or we could convert it to a polars schema via `to_polars` method:

        >>> pl_schema = schema.to_polars()
        >>> type(pl_schema)
        <class 'polars.schema.Schema'>

        >>> pl_schema
        Schema([('name', String), ('age', UInt64), ('classes', List(String))])

    Methods:
        to_arrow():
            Converts the underlying Pydantic model schema into a `pyarrow.Schema`.
        to_pandas():
            Converts the underlying Pydantic model schema into a `dict[str, str | pd.ArrowDtype]`.
        to_polars():
            Converts the underlying Pydantic model schema into a `polars.Schema`.
    """

    def __init__(
        self: Self,
        schema: Schema | IntoOrderedDict | type[BaseModel],
        parsers: IntoParserChain = "auto",
    ) -> None:
        if isinstance(schema, Schema):
            self._nw_schema = schema
        elif isinstance(schema, Mapping) or (isinstance(schema, Sequence) and all(len(s) == 2 for s in schema)):  # noqa: PLR2004
            from anyschema._mapping import mapping_to_nw_schema

            parser_chain = create_parser_chain(parsers, model_type="python")
            self._nw_schema = mapping_to_nw_schema(schema=schema, parser_chain=parser_chain)

        elif is_pydantic_base_model(schema):
            from anyschema._pydantic import model_to_nw_schema

            parser_chain = create_parser_chain(parsers, model_type="pydantic")
            self._nw_schema = model_to_nw_schema(schema=schema, parser_chain=parser_chain)

        else:
            raise NotImplementedError

    def to_arrow(self: Self) -> pa.Schema:
        """Converts input model into pyarrow schema.

        Returns:
            The converted pyarrow schema.
        """
        return self._nw_schema.to_arrow()

    def to_pandas(
        self: Self, *, dtype_backend: DTypeBackend | Iterable[DTypeBackend] = None
    ) -> dict[str, str | pd.ArrowDtype | type]:
        """Converts input model into mapping of {field_name: pandas_dtype}.

        Arguments:
            dtype_backend: which kind of data type backend to use.

        Returns:
            The converted pandas schema.
        """
        return self._nw_schema.to_pandas(dtype_backend=dtype_backend)

    def to_polars(self: Self) -> pl.Schema:
        """Converts input model into polars Schema.

        Returns:
            The converted polars schema.
        """
        return self._nw_schema.to_polars()
