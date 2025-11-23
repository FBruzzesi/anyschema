from __future__ import annotations

import narwhals as nw
from pydantic import BaseModel, StrictBool

from anyschema.parsers import make_pipeline
from tests.pydantic.utils import model_to_nw_schema

pipeline = make_pipeline("auto", spec_type="pydantic")


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

    schema = model_to_nw_schema(BooleanModel, pipeline=pipeline)

    assert all(value == nw.Boolean() for value in schema.values())
