from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal

import narwhals
import pandas as pd
import pyarrow as pa
import pytest
from narwhals.utils import parse_version

from anyschema import AnySchema

if TYPE_CHECKING:
    from pydantic import BaseModel

list_type = pd.ArrowDtype(pa.list_(pa.string()))


@pytest.mark.skipif(parse_version(narwhals.__version__) < (1, 23), reason="too old for converting to pandas")
@pytest.mark.parametrize(
    ("dtype_backend", "expected"),
    [
        ("numpy", {"name": str, "age": "uint64", "classes": list_type}),
        ("pandas-nullable", {"name": "string", "age": "UInt64", "classes": list_type}),
        ("pyarrow-nullable", {"name": "string[pyarrow]", "age": "UInt64[pyarrow]", "classes": list_type}),
    ],
)
def test_to_pandas(
    student_cls: type[BaseModel],
    dtype_backend: Literal["pyarrow-nullable", "pandas-nullable", "numpy"],
    expected: dict[str, str | pd.ArrowDtype | type],
) -> None:
    anyschema = AnySchema(model=student_cls)
    pd_schema = anyschema.to_pandas(dtype_backend=dtype_backend)

    assert isinstance(pd_schema, dict)
    assert pd_schema == expected
