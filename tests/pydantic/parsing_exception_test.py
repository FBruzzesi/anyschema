from __future__ import annotations

from typing import Optional

import pytest
from pydantic import AwareDatetime, create_model

from anyschema._pydantic import model_to_nw_schema
from anyschema.exceptions import UnsupportedDTypeError


@pytest.mark.parametrize(
    ("type_annotation", "msg"),
    [
        (str | float | int, "Union with more than two types is not supported."),
        (str | float, "Union with both types being not None is not supported."),
    ],
)
def test_raise_parse_union(type_annotation: type, msg: str) -> None:
    ExceptionModel = create_model("ExceptionModel", foo=(type_annotation, ...))  # noqa: N806

    with pytest.raises(UnsupportedDTypeError, match=msg):
        model_to_nw_schema(ExceptionModel)


@pytest.mark.parametrize(
    "type_annotation",
    [
        AwareDatetime,
        Optional[AwareDatetime],
        AwareDatetime | None,
        None | AwareDatetime,
    ],
)
def test_raise_aware_datetime(type_annotation: type) -> None:
    AwareDatetimeModel = create_model("AwareDatetimeModel", foo=(type_annotation, ...))  # noqa: N806

    msg = "pydantic AwareDatetime does not specify a fixed timezone."
    with pytest.raises(UnsupportedDTypeError, match=msg):
        model_to_nw_schema(AwareDatetimeModel)
