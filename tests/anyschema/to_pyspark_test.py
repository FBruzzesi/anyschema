from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from narwhals import Schema
from pydantic import BaseModel
from pydantic import Field as PydanticField
from pyspark.sql import types

from anyschema import AnySchema

if TYPE_CHECKING:
    from anyschema.typing import Spec


class User(BaseModel):
    id: int = PydanticField(
        json_schema_extra={
            "anyschema": {"nullable": False},
            "description": "User ID",  # Description outside anyschema namespace will end up in Field metadata
        }
    )
    username: str = PydanticField(json_schema_extra={"anyschema": {"nullable": True}})
    email: str | None


class Product(BaseModel):
    name: str | None = PydanticField(
        json_schema_extra={
            "anyschema": {"nullable": False, "description": "Product name"},
            "max_length": 100,
        }
    )
    price: float = PydanticField(
        json_schema_extra={
            "anyschema": {"nullable": True},
            "currency": "USD",
            "min": 0,
        }
    )


def test_nw_schema_to_pyspark(nw_schema: Schema) -> None:
    unsupported_dtypes = {
        "categorical",
        "decimal",
        "duration",
        "enum",
        "int128",
        "object",
        "time",
        "uint64",
        "uint32",
        "uint16",
        "uint8",
        "unknown",
    }

    model = Schema({k: v for k, v in nw_schema.items() if k not in unsupported_dtypes})
    anyschema = AnySchema(spec=model)
    spark_schema = anyschema.to_pyspark()

    assert isinstance(spark_schema, types.StructType)

    names_and_dtypes = (
        ("array", types.ArrayType(types.IntegerType())),
        ("boolean", types.BooleanType()),
        ("date", types.DataType()),
        ("datetime", types.TimestampNTZType()),
        ("float32", types.FloatType()),
        ("float64", types.DoubleType()),
        ("int8", types.ByteType()),
        ("int16", types.ShortType()),
        ("int32", types.IntegerType()),
        ("int64", types.LongType()),
        ("list", types.ArrayType(types.FloatType())),
        ("string", types.StringType()),
        (
            "struct",
            types.StructType(
                fields=[
                    types.StructField("field_1", types.StringType(), nullable=False, metadata=None),
                    types.StructField("field_2", types.BooleanType(), nullable=False, metadata=None),
                ]
            ),
        ),
    )
    assert spark_schema == types.StructType(
        [types.StructField(*name_and_dtype, nullable=False, metadata=None) for name_and_dtype in names_and_dtypes]
    )


@pytest.mark.parametrize(
    ("spec", "expected_nullable"),
    [
        ({"id": int, "name": str, "email": None | str}, (False, False, True)),
        (User, (False, True, True)),
        (Product, (False, True)),
    ],
)
def test_to_pyspark_nullable_flags(spec: Spec, expected_nullable: tuple[bool, ...]) -> None:
    schema = AnySchema(spec=spec)
    spark_schema = schema.to_pyspark()

    for field, nullable in zip(spark_schema, expected_nullable, strict=True):
        assert field.nullable is nullable


@pytest.mark.parametrize(
    ("spec", "expected_metadata"),
    [
        ({"id": int, "name": str, "email": None | str}, (None, None, None)),
        (User, ({"description": "User ID"}, None, None)),
        (Product, ({"max_length": 100}, {"currency": "USD", "min": 0})),
    ],
)
def test_to_pyspark_with_metadata(spec: Spec, expected_metadata: tuple[dict[bytes, bytes], ...]) -> None:
    schema = AnySchema(spec=spec)
    spark_schema = schema.to_pyspark()

    for field, _metadata in zip(spark_schema, expected_metadata, strict=True):
        assert field.metadata == (_metadata or {})
