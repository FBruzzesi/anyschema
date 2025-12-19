from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Optional

import narwhals as nw
import pydantic
import pytest
from narwhals.utils import parse_version
from pydantic import BaseModel, StrictStr

from tests.pydantic.utils import model_to_nw_schema

if TYPE_CHECKING:
    from anyschema.parsers import ParserPipeline


def test_parse_string(auto_pipeline: ParserPipeline) -> None:
    class StringModel(BaseModel):
        # python str type
        py_str: str
        py_str_optional: str | None
        py_str_or_none: str | None
        none_or_py_str: None | str

        # pydantic StrictStr type
        strict_str: StrictStr
        strict_str_optional: StrictStr | None
        strict_str_or_none: StrictStr | None
        none_or_strict_str: None | StrictStr

    schema = model_to_nw_schema(StringModel, pipeline=auto_pipeline)

    assert all(value == nw.String() for value in schema.values())


@pytest.mark.skipif(parse_version(pydantic.__version__) < (2, 1), reason="too old for StringConstraints")
def test_parse_string_with_constraints(auto_pipeline: ParserPipeline) -> None:
    from pydantic import StringConstraints

    str_constraint = StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Z]+$")

    class StringConstraintsModel(BaseModel):
        str_con: Annotated[str, str_constraint]
        str_con_optional: Optional[Annotated[str, str_constraint]]
        str_con_or_none: Annotated[str, str_constraint] | None
        none_or_str_con: None | Annotated[str, str_constraint]

    schema = model_to_nw_schema(StringConstraintsModel, pipeline=auto_pipeline)

    assert all(value == nw.String() for value in schema.values())
