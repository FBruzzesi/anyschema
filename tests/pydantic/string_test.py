from __future__ import annotations

from typing import Annotated

import narwhals as nw
import pydantic
import pytest
from narwhals.utils import parse_version
from pydantic import BaseModel, StrictStr, constr

from anyschema.parsers import create_parser_chain
from tests.pydantic.utils import model_to_nw_schema

parser_chain = create_parser_chain("auto", model_type="pydantic")


def test_parse_string() -> None:
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

        # pydantic constr type
        con_str: constr(to_upper=True)
        con_str_optional: constr(to_lower=True) | None
        con_str_or_none: constr(min_length=3) | None
        none_or_con_str: None | constr(max_length=6)

    schema = model_to_nw_schema(StringModel, parser_chain=parser_chain)

    assert all(value == nw.String() for value in schema.values())


@pytest.mark.skipif(parse_version(pydantic.__version__) < (2, 1), reason="too old for StringConstraints")
def test_parse_string_constraints() -> None:
    from pydantic import StringConstraints

    str_constraint = StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Z]+$")

    class StringConstraintsModel(BaseModel):
        str_con: Annotated[str, str_constraint]
        str_con_optional: Annotated[str, str_constraint] | None
        str_con_or_none: Annotated[str, str_constraint] | None
        none_or_str_con: None | Annotated[str, str_constraint]

    schema = model_to_nw_schema(StringConstraintsModel, parser_chain=parser_chain)

    assert all(value == nw.String() for value in schema.values())
