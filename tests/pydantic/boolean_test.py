from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw
from pydantic import BaseModel, StrictBool

from tests.pydantic.utils import model_to_nw_schema

if TYPE_CHECKING:
    from anyschema.parsers import ParserPipeline


def test_parse_boolean(auto_pipeline: ParserPipeline) -> None:
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

    schema = model_to_nw_schema(BooleanModel, pipeline=auto_pipeline)

    assert all(value == nw.Boolean() for value in schema.values())
