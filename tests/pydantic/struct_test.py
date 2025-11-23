from __future__ import annotations

import narwhals as nw
from pydantic import BaseModel, conint

from anyschema.parsers import make_pipeline
from tests.pydantic.utils import model_to_nw_schema

pipeline = make_pipeline("auto", spec_type="pydantic")


def test_parse_struct() -> None:
    class BaseStruct(BaseModel):
        x1: conint(gt=0, lt=123)
        x2: str
        x3: float | None
        x4: None | bool

    class StructModel(BaseModel):
        struct: BaseStruct | None

    schema = model_to_nw_schema(StructModel, pipeline=pipeline)
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
