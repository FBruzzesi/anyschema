from __future__ import annotations

from typing import Optional

import narwhals as nw
from pydantic import BaseModel
from pydantic import conint

from anyschema._pydantic import model_to_nw_schema


def test_parse_struct() -> None:
    class BaseStruct(BaseModel):
        x1: conint(gt=0, lt=123)
        x2: str
        x3: float | None
        x4: None | bool

    class StructModel(BaseModel):
        struct: Optional[BaseStruct]  # noqa: UP007

    schema = model_to_nw_schema(StructModel)
    expected = {
        "struct": nw.Struct(
            [
                nw.Field("x1", nw.UInt8()),
                nw.Field("x2", nw.String()),
                nw.Field("x3", nw.Float64()),
                nw.Field("x4", nw.Boolean()),
            ]
        )
    }
    assert schema == expected
