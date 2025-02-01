from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl
from narwhals import Schema

from anyschema import AnySchema

if TYPE_CHECKING:
    from pydantic import BaseModel


def test_pydantic_to_polars(student_cls: type[BaseModel]) -> None:
    anyschema = AnySchema(model=student_cls)
    pl_schema = anyschema.to_polars()

    assert isinstance(pl_schema, pl.Schema)
    assert pl_schema == pl.Schema(
        {
            "name": pl.String(),
            "date_of_birth": pl.Date(),
            "age": pl.UInt64(),
            "classes": pl.List(pl.String()),
            "has_graduated": pl.Boolean(),
        }
    )


def test_nw_schema_to_arrow(nw_schema: Schema) -> None:
    unsupported_dtypes = {"array", "enum", "uint128", "int128", "decimal"}
    model = Schema({k: v for k, v in nw_schema.items() if k not in unsupported_dtypes})
    anyschema = AnySchema(model=model)
    pl_schema = anyschema.to_polars()

    assert isinstance(pl_schema, pl.Schema)
    assert pl_schema == pl.Schema(
        {
            "boolean": pl.Boolean(),
            "categorical": pl.Categorical(),
            "date": pl.Date(),
            "datetime": pl.Datetime(),
            "duration": pl.Duration(),
            "float32": pl.Float32(),
            "float64": pl.Float64(),
            "int8": pl.Int8(),
            "int16": pl.Int16(),
            "int32": pl.Int32(),
            "int64": pl.Int64(),
            "list": pl.List(pl.Float32()),
            "object": pl.Object(),
            "string": pl.String(),
            "struct": pl.Struct(fields=[pl.Field("field_1", pl.String()), pl.Field("field_2", pl.Boolean())]),
            "uint8": pl.UInt8(),
            "uint16": pl.UInt16(),
            "uint32": pl.UInt32(),
            "uint64": pl.UInt64(),
            "unknown": pl.Unknown(),
        }
    )
