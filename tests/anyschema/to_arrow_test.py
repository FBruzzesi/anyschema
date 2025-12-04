from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa
from narwhals import Schema

from anyschema import AnySchema

if TYPE_CHECKING:
    from pydantic import BaseModel


def test_pydantic_to_arrow(pydantic_student_cls: type[BaseModel]) -> None:
    anyschema = AnySchema(spec=pydantic_student_cls)
    pa_schema = anyschema.to_arrow()

    assert isinstance(pa_schema, pa.Schema)
    assert pa_schema == pa.schema(
        [
            ("name", pa.string()),
            ("date_of_birth", pa.date32()),
            ("age", pa.uint64()),
            ("classes", pa.list_(pa.string())),
            ("has_graduated", pa.bool_()),
        ]
    )


def test_nw_schema_to_arrow(nw_schema: Schema) -> None:
    unsupported_dtypes = {"array", "int128", "uint128", "decimal", "enum", "object", "unknown"}
    model = Schema({k: v for k, v in nw_schema.items() if k not in unsupported_dtypes})
    anyschema = AnySchema(spec=model)
    pa_schema = anyschema.to_arrow()

    assert isinstance(pa_schema, pa.Schema)
    assert pa_schema == pa.schema(
        [
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
            (
                "struct",
                pa.struct(
                    [
                        ("field_1", pa.string()),
                        ("field_2", pa.bool_()),
                    ]
                ),
            ),
            ("uint8", pa.uint8()),
            ("uint16", pa.uint16()),
            ("uint32", pa.uint32()),
            ("uint64", pa.uint64()),
        ]
    )
