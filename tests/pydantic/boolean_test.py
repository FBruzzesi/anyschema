from __future__ import annotations

import narwhals as nw
from pydantic import BaseModel, StrictBool

from anyschema.parsers import create_parser_chain
from tests.pydantic.utils import model_to_nw_schema

parser_chain = create_parser_chain("auto", model_type="pydantic")


def test_parse_boolean() -> None:
    class BooleanModel(BaseModel):
        # python bool type
        py_bool: bool
        py_bool_optional: bool | None
        py_bool_or_none: bool | None
        none_or_py_bool: None | bool

        # pydantic StrictBool type
        strict_bool: StrictBool
        strict_bool_optional: StrictBool | None
        strict_bool_or_none: StrictBool | None
        none_or_strict_bool: None | StrictBool

    schema = model_to_nw_schema(BooleanModel, parser_chain=parser_chain)

    assert all(value == nw.Boolean() for value in schema.values())
