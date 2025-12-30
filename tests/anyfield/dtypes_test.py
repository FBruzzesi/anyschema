from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

import narwhals as nw
import pytest

from anyschema import AnySchema

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    AnyDict: TypeAlias = dict[str, Any]


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ({"x": int}, (nw.Int64(),)),
        ({"x": str}, (nw.String(),)),
        ({"x": float}, (nw.Float64(),)),
        ({"x": bool}, (nw.Boolean(),)),
        ({"x": list[int]}, (nw.List(nw.Int64()),)),
        ({"id": int, "name": str, "score": float}, (nw.Int64(), nw.String(), nw.Float64())),
    ],
)
def test_dtypes(spec: AnyDict, expected: tuple[DType, ...]) -> None:
    schema = AnySchema(spec=spec)

    result_tuple = schema.dtypes()
    assert result_tuple == expected

    result_dict = schema.dtypes(named=True)
    assert result_dict == dict(zip(spec.keys(), expected, strict=True))
