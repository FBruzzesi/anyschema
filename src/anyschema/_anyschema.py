from __future__ import annotations

from importlib import metadata
from typing import TYPE_CHECKING
from typing import Literal

from narwhals.schema import Schema
from narwhals.utils import Version
from narwhals.utils import parse_version

from anyschema._dependencies import get_pydantic

if TYPE_CHECKING:
    import pandas as pd
    import polars as pl
    import pyarrow as pa
    from pydantic import BaseModel
    from typing_extensions import Self


NARWHALS_VERSION = parse_version(metadata.version("narwhals"))


class AnySchema:
    """A utility class for converting Pydantic models into schemas compatible with `pyarrow` and `polars`.

    The `AnySchema` class bridges the gap between Pydantic models and popular dataframe libraries like
    `pyarrow` and `polars`, enabling seamless integration of model definitions into data processing pipelines.

    This class takes a Pydantic `BaseModel` or its subclass as input and provides methods to generate
    equivalent dataframe schemas.

    Arguments:
        model: The input model.

    Raises:
        NotImplementedError:
            If the provided model is not a valid Pydantic `BaseModel`, its subclass or instance

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
        import pyarrow as pa
        from narwhals._arrow.utils import narwhals_to_native_dtype

        return pa.schema(
            [
                (field_name, narwhals_to_native_dtype(field_type, Version.MAIN))
                for field_name, field_type in self._nw_schema.items()
            ]
        )

    def to_pandas(
        self: Self,
        *,
        dtype_backend: Literal["pyarrow-nullable", "pandas-nullable", "numpy"] = "numpy",
    ) -> dict[str, str | pd.ArrowDtype | type]:
        """Converts input model into mapping of {field_name: pandas_dtype}.

        Arguments:
            dtype_backend: which kind of data type backend to use.

        Returns:
            The converted pandas schema.
        """
        if NARWHALS_VERSION < (1, 23):  # pragma: no cover
            msg = (
                "Converting to pandas requires narwhals>=1.23 to be installed, "
                f"found narwhals=={NARWHALS_VERSION} instead. Please upgrade to a newer version."
            )
            raise NotImplementedError(msg)

        import pandas as pd
        from narwhals._pandas_like.utils import narwhals_to_native_dtype
        from narwhals.utils import Implementation
        from narwhals.utils import parse_version

        pd_version = parse_version(pd.__version__)
        return {
            field_name: narwhals_to_native_dtype(
                field_type,
                dtype_backend=dtype_backend,
                implementation=Implementation.PANDAS,
                backend_version=pd_version,
                version=Version.MAIN,
            )
            for field_name, field_type in self._nw_schema.items()
        }

    def to_polars(self: Self) -> pl.Schema:
        """Converts input model into polars Schema.

        Returns:
            The converted polars schema.
        """
        import polars as pl
        from narwhals._polars.utils import narwhals_to_native_dtype

        return pl.Schema(
            {
                field_name: narwhals_to_native_dtype(field_type, Version.MAIN)
                for field_name, field_type in self._nw_schema.items()
            }
        )
