from __future__ import annotations

from typing import Optional

import narwhals as nw
from pydantic import BaseModel
from pydantic import StrictBool

from anyschema._pydantic import model_to_nw_schema


def test_parse_boolean() -> None:
    class BooleanModel(BaseModel):
        # python bool type
        py_bool: bool
        py_bool_optional: Optional[bool]  # noqa: UP007
        py_bool_or_none: bool | None
        none_or_py_bool: None | bool

        # pydantic StrictBool type
        strict_bool: StrictBool
        strict_bool_optional: Optional[StrictBool]  # noqa: UP007
        strict_bool_or_none: StrictBool | None
        none_or_strict_bool: None | StrictBool

    schema = model_to_nw_schema(BooleanModel)

    assert all(value == nw.Boolean() for value in schema.values())
