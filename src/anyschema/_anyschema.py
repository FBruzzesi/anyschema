from __future__ import annotations

from typing import TYPE_CHECKING

from narwhals.utils import Version
from narwhals.utils import isinstance_or_issubclass

from anyschema._dependencies import get_pydantic

if TYPE_CHECKING:
    import polars as pl
    import pyarrow as pa
    from pydantic import BaseModel
    from typing_extensions import Self


class AnySchema:
    """AnySchema class.

    Example:
        >>> from anyschema import AnySchema
        >>> from pydantic import BaseModel
        >>>
        >>> class MyModel(BaseModel):
        ...     name: str
        ...     age: int
        >>>
        >>> schema = AnySchema(MyModel)
        >>> schema.to_arrow()
        name: string
        age: int64

        >>> schema.to_polars()
        Schema([('name', String), ('age', Int64)])
    """

    def __init__(self: Self, model: BaseModel | type[BaseModel]) -> None:
        """Initializes an instance of AnySchema from a pydantic BaseModel.

        Arguments:
            model: The input model to be converted into a schema.
        """
        if (pydantic := get_pydantic()) is not None and isinstance_or_issubclass(model, pydantic.BaseModel):
            from anyschema._pydantic import model_to_nw_schema

            self._type = "pydantic"
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
