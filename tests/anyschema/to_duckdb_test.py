from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
import narwhals as nw
import polars as pl
import pytest

from anyschema import AnySchema
from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from narwhals.typing import IntoDType
    from pydantic import BaseModel


def _duckdb_type_names(schema: AnySchema) -> dict[str, str]:
    return {name: str(dtype) for name, dtype in schema.to_duckdb().items()}


def test_pydantic_to_duckdb(pydantic_student_cls: type[BaseModel]) -> None:
    assert _duckdb_type_names(AnySchema(spec=pydantic_student_cls)) == {
        "name": "VARCHAR",
        "date_of_birth": "DATE",
        "age": "UBIGINT",
        "classes": "VARCHAR[]",
        "has_graduated": "BOOLEAN",
    }


def test_nw_schema_to_duckdb(nw_schema: nw.Schema) -> None:
    unsupported_dtypes = {"categorical", "object", "unknown"}
    model = nw.Schema({k: v for k, v in nw_schema.items() if k not in unsupported_dtypes})

    assert _duckdb_type_names(AnySchema(spec=model)) == {
        "array": "INTEGER[3]",
        "boolean": "BOOLEAN",
        "date": "DATE",
        "datetime": "TIMESTAMP",
        "decimal": "DECIMAL(38,0)",
        "duration": "INTERVAL",
        "enum": "ENUM('foo', 'bar')",
        "float32": "FLOAT",
        "float64": "DOUBLE",
        "int8": "TINYINT",
        "int16": "SMALLINT",
        "int32": "INTEGER",
        "int64": "BIGINT",
        "int128": "HUGEINT",
        "list": "FLOAT[]",
        "string": "VARCHAR",
        "struct": "STRUCT(field_1 VARCHAR, field_2 BOOLEAN)",
        "uint8": "UTINYINT",
        "uint16": "USMALLINT",
        "uint32": "UINTEGER",
        "uint64": "UBIGINT",
        "uint128": "UHUGEINT",
    }


@pytest.mark.parametrize(
    ("dtype", "expected"),
    [
        (nw.Datetime("us", "Europe/Rome"), "TIMESTAMP WITH TIME ZONE"),
        (nw.Datetime("ns"), "TIMESTAMP_NS"),
        (nw.List(nw.Struct({"ts": nw.Datetime("us", "UTC")})), "STRUCT(ts TIMESTAMP WITH TIME ZONE)[]"),
        (nw.Array(nw.Int32(), (2, 3)), "INTEGER[3][2]"),
        (nw.Enum(["it's", "ok"]), "ENUM('it''s', 'ok')"),
        (nw.List(nw.Int64), "BIGINT[]"),
    ],
)
def test_to_duckdb_special_dtypes(dtype: IntoDType, expected: str) -> None:
    result = AnySchema(spec=nw.Schema({"x": dtype})).to_duckdb()["x"]

    assert str(result) == expected
    duckdb.sql(f"select null::{result} as x")  # the type must be valid DuckDB SQL


def test_to_duckdb_array_shape_roundtrip() -> None:
    result = AnySchema(spec=nw.Schema({"x": nw.Array(nw.Int32(), (2, 3))})).to_duckdb()["x"]
    rel = duckdb.sql(f"select [[1, 2, 3], [4, 5, 6]]::{result} as x")

    # DuckDB's own export is the reference: narwhals reads DuckDB multi-dim arrays with a transposed shape.
    assert rel.pl().schema["x"] == pl.Array(pl.Int32, (2, 3))  # type: ignore[union-attr]


def test_to_duckdb_tz_aware_non_us_raises() -> None:
    schema = AnySchema(spec=nw.Schema({"x": nw.Datetime("ns", "UTC")}))

    with pytest.raises(UnsupportedDTypeError, match="microsecond precision"):
        schema.to_duckdb()


@pytest.mark.parametrize("dtype", [nw.Categorical(), nw.Object(), nw.Unknown(), nw.List(nw.Object)])
def test_to_duckdb_unsupported_dtype_raises(dtype: IntoDType) -> None:
    schema = AnySchema(spec=nw.Schema({"x": dtype}))

    with pytest.raises(UnsupportedDTypeError, match="has no DuckDB equivalent"):
        schema.to_duckdb()
