from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw
from pydantic import BaseModel, conint

from tests.pydantic.utils import model_to_nw_schema

if TYPE_CHECKING:
    from anyschema.parsers import ParserPipeline


def test_parse_struct(auto_pipeline: ParserPipeline) -> None:
    class BaseStruct(BaseModel):
        x1: conint(gt=0, lt=123)
        x2: str
        x3: float | None
        x4: None | bool

    class StructModel(BaseModel):
        struct: BaseStruct | None

    schema = model_to_nw_schema(StructModel, pipeline=auto_pipeline)
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
