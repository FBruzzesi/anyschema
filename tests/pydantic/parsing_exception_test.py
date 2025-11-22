from __future__ import annotations

from typing import Optional

import pytest
from pydantic import AwareDatetime, create_model

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers import create_parser_chain
from tests.pydantic.utils import model_to_nw_schema

parser_chain = create_parser_chain("auto", model_type="pydantic")


@pytest.mark.parametrize(
    ("input_type", "msg"),
    [
        (str | float | int, "Union with more than two types is not supported."),
        (str | float, "Union with both types being not None is not supported."),
    ],
)
def test_raise_parse_union(input_type: type, msg: str) -> None:
    ExceptionModel = create_model("ExceptionModel", foo=(input_type, ...))  # noqa: N806

    with pytest.raises(UnsupportedDTypeError, match=msg):
        model_to_nw_schema(ExceptionModel, parser_chain=parser_chain)


@pytest.mark.parametrize(
    "input_type",
    [
        AwareDatetime,
        Optional[AwareDatetime],
        AwareDatetime | None,
        None | AwareDatetime,
    ],
)
def test_raise_aware_datetime(input_type: type) -> None:
    AwareDatetimeModel = create_model("AwareDatetimeModel", foo=(input_type, ...))  # noqa: N806

    msg = "pydantic AwareDatetime does not specify a fixed timezone."
    with pytest.raises(UnsupportedDTypeError, match=msg):
        model_to_nw_schema(AwareDatetimeModel, parser_chain=parser_chain)
