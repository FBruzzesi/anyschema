from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa
import pytest
from narwhals import Schema
from pydantic import BaseModel
from pydantic import Field as PydanticField

from anyschema import AnySchema

if TYPE_CHECKING:
    from anyschema.typing import Spec


class User(BaseModel):
    id: int = PydanticField(json_schema_extra={"anyschema/nullable": False, "description": "User ID"})
    username: str = PydanticField(json_schema_extra={"anyschema/nullable": True})
    email: str | None


class Product(BaseModel):
    name: str | None = PydanticField(
        json_schema_extra={"anyschema/nullable": False, "description": "Product name", "max_length": 100}
    )
    price: float = PydanticField(json_schema_extra={"anyschema/nullable": True, "currency": "USD", "min": 0})


def test_pydantic_to_arrow(pydantic_student_cls: type[BaseModel]) -> None:
    anyschema = AnySchema(spec=pydantic_student_cls)
    pa_schema = anyschema.to_arrow()

    assert isinstance(pa_schema, pa.Schema)
    assert pa_schema == pa.schema(
        [
            pa.field("name", pa.string(), nullable=False),
            pa.field("date_of_birth", pa.date32(), nullable=False),
            pa.field("age", pa.uint64(), nullable=False),
            pa.field("classes", pa.list_(pa.string()), nullable=False),
            pa.field("has_graduated", pa.bool_(), nullable=False),
        ]
    )


def test_nw_schema_to_arrow(nw_schema: Schema) -> None:
    unsupported_dtypes = {"array", "int128", "uint128", "decimal", "enum", "object", "unknown"}
    model = Schema({k: v for k, v in nw_schema.items() if k not in unsupported_dtypes})
    anyschema = AnySchema(spec=model)
    pa_schema = anyschema.to_arrow()

    assert isinstance(pa_schema, pa.Schema)

    struct_dtype = pa.struct([("field_1", pa.string()), ("field_2", pa.bool_())])
    assert pa_schema == pa.schema(
        [
            pa.field("boolean", pa.bool_(), nullable=False),
            pa.field("categorical", pa.dictionary(pa.uint32(), pa.string()), nullable=False),
            pa.field("date", pa.date32(), nullable=False),
            pa.field("datetime", pa.timestamp(unit="us", tz=None), nullable=False),
            pa.field("duration", pa.duration(unit="us"), nullable=False),
            pa.field("float32", pa.float32(), nullable=False),
            pa.field("float64", pa.float64(), nullable=False),
            pa.field("int8", pa.int8(), nullable=False),
            pa.field("int16", pa.int16(), nullable=False),
            pa.field("int32", pa.int32(), nullable=False),
            pa.field("int64", pa.int64(), nullable=False),
            pa.field("list", pa.list_(pa.float32()), nullable=False),
            pa.field("string", pa.string(), nullable=False),
            pa.field("struct", struct_dtype, nullable=False),
            pa.field("uint8", pa.uint8(), nullable=False),
            pa.field("uint16", pa.uint16(), nullable=False),
            pa.field("uint32", pa.uint32(), nullable=False),
            pa.field("uint64", pa.uint64(), nullable=False),
        ]
    )


@pytest.mark.parametrize(
    ("spec", "expected_nullable"),
    [
        ({"id": int, "name": str, "email": None | str}, (False, False, True)),
        (User, (False, True, True)),
        (Product, (False, True)),
    ],
)
def test_to_arrow_nullable_flags(spec: Spec, expected_nullable: tuple[bool, ...]) -> None:
    schema = AnySchema(spec=spec)
    pa_schema = schema.to_arrow()

    for field, nullable in zip(pa_schema, expected_nullable, strict=True):
        assert field.nullable is nullable


@pytest.mark.parametrize(
    ("spec", "expected_metadata"),
    [
        ({"id": int, "name": str, "email": None | str}, (None, None, None)),
        (User, ({b"description": b"User ID"}, None, None)),
        (Product, ({b"description": b"Product name", b"max_length": b"100"}, {b"currency": b"USD", b"min": b"0"})),
    ],
)
def test_to_arrow_with_metadata(spec: Spec, expected_metadata: tuple[bool, ...]) -> None:
    schema = AnySchema(spec=spec)
    pa_schema = schema.to_arrow()

    for field, nullable in zip(pa_schema, expected_metadata, strict=True):
        assert field.metadata == nullable
