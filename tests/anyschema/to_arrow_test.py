from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

import narwhals as nw
import pyarrow as pa
import pytest
from narwhals import Schema
from pydantic import BaseModel
from pydantic import Field as PydanticField

from anyschema import AnySchema

if TYPE_CHECKING:
    from anyschema.typing import Spec

ENUM_ARROW_TYPE = pa.dictionary(pa.uint32(), pa.string())


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


def test_pydantic_to_arrow(pydantic_student_cls: type[BaseModel]) -> None:
    anyschema = AnySchema(spec=pydantic_student_cls)
    pa_schema = anyschema.to_arrow()

    assert isinstance(pa_schema, pa.Schema)
    names_and_types = (
        ("name", pa.string()),
        ("date_of_birth", pa.date32()),
        ("age", pa.uint64()),
        ("classes", pa.list_(pa.string())),
        ("has_graduated", pa.bool_()),
    )
    fields: tuple[pa.Field[Any], ...] = tuple(pa.field(name, dtype, nullable=False) for name, dtype in names_and_types)
    assert pa_schema == pa.schema(fields)


def test_nw_schema_to_arrow(nw_schema: Schema) -> None:
    unsupported_dtypes = {"array", "int128", "uint128", "decimal", "enum", "object", "unknown"}
    model = Schema({k: v for k, v in nw_schema.items() if k not in unsupported_dtypes})
    anyschema = AnySchema(spec=model)
    pa_schema = anyschema.to_arrow()

    assert isinstance(pa_schema, pa.Schema)

    struct_dtype = pa.struct([("field_1", pa.string()), ("field_2", pa.bool_())])
    names_and_dtypes = (
        ("boolean", pa.bool_()),
        ("categorical", pa.dictionary(pa.uint32(), pa.string())),
        ("date", pa.date32()),
        ("datetime", pa.timestamp(unit="us", tz=None)),
        ("duration", pa.duration(unit="us")),
        ("float32", pa.float32()),
        ("float64", pa.float64()),
        ("int8", pa.int8()),
        ("int16", pa.int16()),
        ("int32", pa.int32()),
        ("int64", pa.int64()),
        ("list", pa.list_(pa.float32())),
        ("string", pa.string()),
        ("struct", struct_dtype),
        ("uint8", pa.uint8()),
        ("uint16", pa.uint16()),
        ("uint32", pa.uint32()),
        ("uint64", pa.uint64()),
    )
    assert pa_schema == pa.schema((pa.field(name, dtype, nullable=False) for name, dtype in names_and_dtypes))


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
        (Product, ({b"max_length": b"100"}, {b"currency": b"USD", b"min": b"0"})),
    ],
)
def test_to_arrow_with_metadata(spec: Spec, expected_metadata: tuple[dict[bytes, bytes], ...]) -> None:
    schema = AnySchema(spec=spec)
    pa_schema = schema.to_arrow()

    for field, _metadata in zip(pa_schema, expected_metadata, strict=True):
        assert field.metadata == _metadata


def test_to_arrow_literal_keeps_nullability() -> None:
    pa_schema = AnySchema(spec={"s": Literal["a", "b"], "t": Literal["x"] | None}).to_arrow()

    assert pa_schema == pa.schema(
        [pa.field("s", ENUM_ARROW_TYPE, nullable=False), pa.field("t", ENUM_ARROW_TYPE, nullable=True)]
    )


def test_to_arrow_nested_enum() -> None:
    class Color(Enum):
        RED = "red"
        BLUE = "blue"

    class Inner(BaseModel):
        color: Color

    class Outer(BaseModel):
        colors: list[Color]
        inner: Inner | None

    pa_schema = AnySchema(spec=Outer).to_arrow()

    assert pa_schema == pa.schema(
        [
            pa.field("colors", pa.list_(ENUM_ARROW_TYPE), nullable=False),
            pa.field("inner", pa.struct([("color", ENUM_ARROW_TYPE)]), nullable=True),
        ]
    )


def test_to_arrow_enum_in_array_keeps_shape() -> None:
    pa_schema = AnySchema(spec=Schema({"a": nw.Array(nw.Enum(["x", "y"]), (2, 3))})).to_arrow()

    assert pa_schema.field("a").type == pa.list_(pa.list_(ENUM_ARROW_TYPE, 3), 2)


def test_to_arrow_map_and_float16() -> None:
    spec = Schema(
        {"m": nw.Map(nw.String(), nw.Int64()), "e": nw.Map(nw.String(), nw.Enum(["x", "y"])), "f": nw.Float16()}
    )

    pa_schema = AnySchema(spec=spec).to_arrow()

    assert pa_schema.types == [pa.map_(pa.string(), pa.int64()), pa.map_(pa.string(), ENUM_ARROW_TYPE), pa.float16()]
