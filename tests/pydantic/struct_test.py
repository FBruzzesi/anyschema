from __future__ import annotations

import narwhals as nw
from pydantic import BaseModel, conint

from anyschema._pydantic import model_to_nw_schema
from anyschema.parsers import create_parser_chain

parser_chain = create_parser_chain("auto", model_type="pydantic")


def test_parse_struct() -> None:
    class BaseStruct(BaseModel):
        x1: conint(gt=0, lt=123)
        x2: str
        x3: float | None
        x4: None | bool

    class StructModel(BaseModel):
        struct: BaseStruct | None

    schema = model_to_nw_schema(StructModel, parser_chain=parser_chain)
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
