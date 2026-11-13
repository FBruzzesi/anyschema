from __future__ import annotations

from typing import TYPE_CHECKING

import ibis
import narwhals as nw
import pytest
from pydantic import BaseModel
from pydantic import Field as PydanticField

from anyschema import AnySchema
from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from narwhals.typing import IntoDType


def _ibis_type_names(schema: AnySchema) -> dict[str, str]:
    return {name: str(dtype) for name, dtype in schema.to_ibis().items()}


def test_pydantic_to_ibis(pydantic_student_cls: type[BaseModel]) -> None:
    assert _ibis_type_names(AnySchema(spec=pydantic_student_cls)) == {
        "name": "!string",
        "date_of_birth": "!date",
        "age": "!uint64",
        "classes": "!array<string>",
        "has_graduated": "!boolean",
    }


def test_nw_schema_to_ibis(nw_schema: nw.Schema) -> None:
    unsupported_dtypes = {"categorical", "enum", "int128", "object", "uint128", "unknown"}
    model = nw.Schema({k: v for k, v in nw_schema.items() if k not in unsupported_dtypes})

    assert _ibis_type_names(AnySchema(spec=model)) == {
        "array": "!array<int32, 3>",
        "boolean": "!boolean",
        "date": "!date",
        "datetime": "!timestamp(6)",
        "decimal": "!decimal(38, 0)",
        "duration": "!interval('us')",
        "float32": "!float32",
        "float64": "!float64",
        "int8": "!int8",
        "int16": "!int16",
        "int32": "!int32",
        "int64": "!int64",
        "list": "!array<float32>",
        "string": "!string",
        "struct": "!struct<field_1: string, field_2: boolean>",
        "uint8": "!uint8",
        "uint16": "!uint16",
        "uint32": "!uint32",
        "uint64": "!uint64",
    }


def test_to_ibis_preserves_nullability() -> None:
    class User(BaseModel):
        id: int
        email: str | None
        nickname: str = PydanticField(json_schema_extra={"anyschema": {"nullable": True}})

    result = AnySchema(spec=User).to_ibis()

    assert isinstance(result, ibis.Schema)
    assert {name: dtype.nullable for name, dtype in result.items()} == {"id": False, "email": True, "nickname": True}


@pytest.mark.parametrize(
    ("dtype", "expected"),
    [
        (nw.Datetime("ns", "Europe/Rome"), "!timestamp('Europe/Rome', 9)"),
        (nw.Duration("ms"), "!interval('ms')"),
        (nw.Array(nw.Int32(), (2, 3)), "!array<array<int32, 3>, 2>"),
        (nw.List(nw.Struct({"ts": nw.Datetime("us", "UTC")})), "!array<struct<ts: timestamp('UTC', 6)>>"),
    ],
)
def test_to_ibis_special_dtypes(dtype: IntoDType, expected: str) -> None:
    assert str(AnySchema(spec=nw.Schema({"x": dtype})).to_ibis()["x"]) == expected


@pytest.mark.parametrize(
    "dtype",
    [
        nw.Categorical(),
        nw.Enum(["a", "b"]),
        nw.Int128(),
        nw.UInt128(),
        nw.Object(),
        nw.Unknown(),
        nw.List(nw.Object()),
        nw.Struct({"a": nw.Int128()}),
    ],
)
def test_to_ibis_unsupported_dtype_raises(dtype: IntoDType) -> None:
    schema = AnySchema(spec=nw.Schema({"x": dtype}))

    with pytest.raises(UnsupportedDTypeError, match=r"has no Ibis equivalent \(field 'x'\)"):
        schema.to_ibis()
