from __future__ import annotations

from enum import IntEnum

import narwhals as nw
import pytest
from narwhals import Schema
from narwhals.utils import parse_version
from pydantic import BaseModel

from anyschema import AnySchema
from anyschema.exceptions import UnsupportedDTypeError

pytest.importorskip("polars")
import polars as pl


def test_pydantic_to_polars(pydantic_student_cls: type[BaseModel]) -> None:
    anyschema = AnySchema(spec=pydantic_student_cls)
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
    anyschema = AnySchema(spec=model)
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


def test_int_enum_to_polars() -> None:
    class HttpStatus(IntEnum):
        OK = 200
        NOT_FOUND = 404

    class Response(BaseModel):
        status: HttpStatus

    assert AnySchema(spec=Response).to_polars() == pl.Schema({"status": pl.UInt16()})


@pytest.mark.skipif(parse_version(pl.__version__) < (2,), reason="`Map` needs polars>=2.0")
def test_map_and_float16_to_polars() -> None:
    spec = Schema({"m": nw.Map(nw.String(), nw.Int64()), "f": nw.Float16()})

    assert AnySchema(spec=spec).to_polars() == pl.Schema({"m": pl.Map(pl.String(), pl.Int64()), "f": pl.Float16()})


@pytest.mark.thread_unsafe(reason="patches polars.__version__")
@pytest.mark.parametrize(
    ("polars_version", "dtype", "match"),
    [
        ("1.35.0", nw.Float16(), r"Float16 needs polars>=1.36, found 1.35.0 \(field 'x'\)"),
        ("1.35.0", nw.List(nw.Float16()), r"Float16 needs polars>=1.36"),
        ("1.99.0", nw.Map(nw.String(), nw.Int64()), r"Map needs polars>=2.0, found 1.99.0 \(field 'x'\)"),
        ("1.99.0", nw.Struct({"a": nw.Map(nw.String(), nw.Int64())}), r"Map needs polars>=2.0"),
    ],
)
def test_to_polars_too_old_raises(
    monkeypatch: pytest.MonkeyPatch, polars_version: str, dtype: nw.dtypes.DType, match: str
) -> None:
    monkeypatch.setattr(pl, "__version__", polars_version)
    schema = AnySchema(spec=Schema({"x": dtype}))

    with pytest.raises(UnsupportedDTypeError, match=match):
        schema.to_polars()
