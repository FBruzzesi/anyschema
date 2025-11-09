from __future__ import annotations

from importlib import metadata
from typing import TYPE_CHECKING

from narwhals.schema import Schema
from narwhals.utils import parse_version

from anyschema._dependencies import get_pydantic

if TYPE_CHECKING:
    from collections.abc import Iterable

    import pandas as pd
    import polars as pl
    import pyarrow as pa
    from narwhals.typing import DTypeBackend
    from pydantic import BaseModel
    from typing_extensions import Self


NARWHALS_VERSION = parse_version(metadata.version("narwhals"))


class AnySchema:
    """A utility class for converting from a model-like to a native dataframe schema object.

    The `AnySchema` class bridges the gap between Narwhals' Schemas and Pydantic Models, and popular dataframe libraries
    such as `pandas`, `polars` and `pyarrow`, by enabling converting from the former to latter native schemas.

    This class takes a Pydantic `BaseModel` or its subclass as input and provides methods to generate
    equivalent dataframe schemas.

    Arguments:
        model: The input model. This can be:

            - a [Narwhals Schema](https://narwhals-dev.github.io/narwhals/api-reference/schema/#narwhals.schema.Schema)
            - a [Pydantic Model](https://docs.pydantic.dev/latest/concepts/models/) class or an instance of such

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
        >>> schema = AnySchema(model=Student)

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

    def __init__(self: Self, model: Schema | BaseModel | type[BaseModel]) -> None:
        if isinstance(model, Schema):
            self._nw_schema = model

        elif (pydantic := get_pydantic()) is not None and (
            (isinstance(model, type) and issubclass(model, pydantic.BaseModel)) or isinstance(model, pydantic.BaseModel)
        ):
            from anyschema._pydantic import model_to_nw_schema

            self._nw_schema = model_to_nw_schema(model=model)

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
