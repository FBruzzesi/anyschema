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
    def __init__(self: Self, model: BaseModel) -> None:
        if (pydantic := get_pydantic()) is not None and isinstance_or_issubclass(model, pydantic.BaseModel):
            from anyschema._pydantic import model_to_nw_schema

            self._type = "pydantic"
            self._nw_schema = model_to_nw_schema(model=model)

        else:
            raise NotImplementedError

    def to_arrow(self: Self) -> pa.Schema:
        """Converts input model into pyarrow schema.

        Returns:
            pyarrow Schema
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
            polars Schema
        """
        import polars as pl
        from narwhals._polars.utils import narwhals_to_native_dtype

        return pl.Schema(
            {
                field_name: narwhals_to_native_dtype(field_type, Version.MAIN)
                for field_name, field_type in self._nw_schema.items()
            }
        )

    @classmethod
    def from_pydantic(cls: type[Self], model: BaseModel) -> Self:
        """Instantiate AnySchema object from pydantic class.

        Returns:
            AnySchema instance
        """
        return AnySchema(model=model)
