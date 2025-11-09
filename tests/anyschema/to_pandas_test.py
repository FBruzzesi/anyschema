from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw
import pandas as pd
import pyarrow as pa
import pytest

from anyschema import AnySchema

if TYPE_CHECKING:
    from narwhals.typing import DTypeBackend
    from pydantic import BaseModel


@pytest.mark.parametrize(
    ("dtype_backend", "expected"),
    [
        (
            None,
            {
                "name": str,
                "date_of_birth": "date32[pyarrow]",
                "age": "uint64",
                "classes": pd.ArrowDtype(pa.list_(pa.string())),
                "has_graduated": "bool",
            },
        ),
        (
            "numpy_nullable",
            {
                "name": "string",
                "date_of_birth": "date32[pyarrow]",
                "age": "UInt64",
                "classes": pd.ArrowDtype(pa.list_(pa.string())),
                "has_graduated": "boolean",
            },
        ),
        (
            "pyarrow",
            {
                "name": "string[pyarrow]",
                "date_of_birth": "date32[pyarrow]",
                "age": "UInt64[pyarrow]",
                "classes": pd.ArrowDtype(pa.list_(pa.string())),
                "has_graduated": "boolean[pyarrow]",
            },
        ),
    ],
)
def test_pydantic_to_pandas(
    student_cls: type[BaseModel],
    dtype_backend: DTypeBackend,
    expected: dict[str, str | pd.ArrowDtype | type],
) -> None:
    anyschema = AnySchema(model=student_cls)
    pd_schema = anyschema.to_pandas(dtype_backend=dtype_backend)
    assert isinstance(pd_schema, dict)
    assert pd_schema == expected


@pytest.mark.parametrize(
    ("dtype_backend", "expected"),
    [
        (
            None,
            {
                "boolean": "bool",
                "categorical": "category",
                "date": "date32[pyarrow]",
                "datetime": "datetime64[us]",
                "duration": "timedelta64[us]",
                "float32": "float32",
                "float64": "float64",
                "int8": "int8",
                "int16": "int16",
                "int32": "int32",
                "int64": "int64",
                "list": pd.ArrowDtype(pa.list_(pa.float32())),
                "string": str,
                "struct": pd.ArrowDtype(
                    pa.struct(
                        [
                            ("field_1", pa.string()),
                            ("field_2", pa.bool_()),
                        ]
                    )
                ),
                "uint8": "uint8",
                "uint16": "uint16",
                "uint32": "uint32",
                "uint64": "uint64",
            },
        ),
        (
            "numpy_nullable",
            {
                "boolean": "boolean",
                "categorical": "category",
                "date": "date32[pyarrow]",
                "datetime": "datetime64[us]",
                "duration": "timedelta64[us]",
                "float32": "Float32",
                "float64": "Float64",
                "int8": "Int8",
                "int16": "Int16",
                "int32": "Int32",
                "int64": "Int64",
                "list": pd.ArrowDtype(pa.list_(pa.float32())),
                "string": "string",
                "struct": pd.ArrowDtype(
                    pa.struct(
                        [
                            ("field_1", pa.string()),
                            ("field_2", pa.bool_()),
                        ]
                    )
                ),
                "uint8": "UInt8",
                "uint16": "UInt16",
                "uint32": "UInt32",
                "uint64": "UInt64",
            },
        ),
        (
            "pyarrow",
            {
                "boolean": "boolean[pyarrow]",
                "categorical": "category",
                "date": "date32[pyarrow]",
                "datetime": "timestamp[us][pyarrow]",
                "duration": "duration[us][pyarrow]",
                "float32": "Float32[pyarrow]",
                "float64": "Float64[pyarrow]",
                "int8": "Int8[pyarrow]",
                "int16": "Int16[pyarrow]",
                "int32": "Int32[pyarrow]",
                "int64": "Int64[pyarrow]",
                "list": pd.ArrowDtype(pa.list_(pa.float32())),
                "string": "string[pyarrow]",
                "struct": pd.ArrowDtype(
                    pa.struct(
                        [
                            ("field_1", pa.string()),
                            ("field_2", pa.bool_()),
                        ]
                    )
                ),
                "uint8": "UInt8[pyarrow]",
                "uint16": "UInt16[pyarrow]",
                "uint32": "UInt32[pyarrow]",
                "uint64": "UInt64[pyarrow]",
            },
        ),
    ],
)
def test_nw_schema_to_arrow(
    nw_schema: nw.Schema,
    dtype_backend: DTypeBackend,
    expected: dict[str, str | pd.ArrowDtype | type],
) -> None:
    unsupported_dtypes = {"array", "enum", "uint128", "int128", "decimal", "object", "unknown"}
    model = nw.Schema({k: v for k, v in nw_schema.items() if k not in unsupported_dtypes})
    anyschema = AnySchema(model=model)
    pd_schema = anyschema.to_pandas(dtype_backend=dtype_backend)

    assert isinstance(pd_schema, dict)
    assert pd_schema == expected
