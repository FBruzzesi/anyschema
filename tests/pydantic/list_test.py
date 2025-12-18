from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Optional

import narwhals as nw
from annotated_types import Interval, Len
from pydantic import BaseModel

from tests.pydantic.utils import model_to_nw_schema

if TYPE_CHECKING:
    from anyschema.parsers import ParserPipeline


def test_parse_list_optional_outer(auto_pipeline: ParserPipeline) -> None:
    class ListModel(BaseModel):
        # python list[...] type
        py_list: list[int]
        py_list_optional: list[str] | None
        py_list_or_none: list[float] | None
        none_or_py_list: None | list[bool]

        # pydantic conlist type
        con_list: Annotated[list[int], Len(min_length=2)]
        con_list_optional: Optional[Annotated[list[str], Len(max_length=6)]]
        con_list_or_none: Annotated[list[float], Len(0)] | None
        none_or_con_list: None | Annotated[list[bool], Len(0)]

    schema = model_to_nw_schema(ListModel, pipeline=auto_pipeline)
    expected = {
        "py_list": nw.List(nw.Int64()),
        "py_list_optional": nw.List(nw.String()),
        "py_list_or_none": nw.List(nw.Float64()),
        "none_or_py_list": nw.List(nw.Boolean()),
        "con_list": nw.List(nw.Int64()),
        "con_list_optional": nw.List(nw.String()),
        "con_list_or_none": nw.List(nw.Float64()),
        "none_or_con_list": nw.List(nw.Boolean()),
    }
    assert schema == expected


def test_parse_list_optional_inner(auto_pipeline: ParserPipeline) -> None:
    class ListModel(BaseModel):
        # python list[...] type
        py_list_optional: list[str | None]
        py_list_or_none: list[float | None] | None
        none_or_py_list: list[None | bool]

        # pydantic conlist type
        con_list_optional: Annotated[list[Optional[int]], Len(min_length=2)]
        con_list_or_none: Annotated[list[str | None], Len(max_length=6)]
        none_or_con_list: Annotated[list[None | float], Len(0)]

    schema = model_to_nw_schema(ListModel, pipeline=auto_pipeline)
    expected = {
        "py_list_optional": nw.List(nw.String()),
        "py_list_or_none": nw.List(nw.Float64()),
        "none_or_py_list": nw.List(nw.Boolean()),
        "con_list_optional": nw.List(nw.Int64()),
        "con_list_or_none": nw.List(nw.String()),
        "none_or_con_list": nw.List(nw.Float64()),
    }
    assert schema == expected


def test_parse_list_optional_outer_and_inner(auto_pipeline: ParserPipeline) -> None:
    class ListModel(BaseModel):
        # python list[...] type
        py_list_optional_optional: list[int | None] | None
        py_list_optional_none: list[str | None] | None
        py_list_none_optional: list[float | None] | None
        py_list_none_none: list[None | bool] | None

        # pydantic conlist type
        con_list_optional_optional: Optional[Annotated[list[Optional[int]], Len(min_length=2)]]
        con_list_optional_none: Annotated[list[Optional[str]], Len(max_length=6)] | None
        con_list_none_optional: Optional[Annotated[list[float | None], Len(0)]]
        con_list_none_none: Annotated[list[None | bool], Len(0)] | None

    schema = model_to_nw_schema(ListModel, pipeline=auto_pipeline)
    expected = {
        "py_list_optional_optional": nw.List(nw.Int64()),
        "py_list_optional_none": nw.List(nw.String()),
        "py_list_none_optional": nw.List(nw.Float64()),
        "py_list_none_none": nw.List(nw.Boolean()),
        "con_list_optional_optional": nw.List(nw.Int64()),
        "con_list_optional_none": nw.List(nw.String()),
        "con_list_none_optional": nw.List(nw.Float64()),
        "con_list_none_none": nw.List(nw.Boolean()),
    }
    assert schema == expected


def test_parse_conlist_conint(auto_pipeline: ParserPipeline) -> None:
    class ListModel(BaseModel):
        # python list[...] type
        py_list_int8: list[Annotated[int, Interval(gt=-64, lt=64)]] | None
        py_list_uint8: list[Annotated[int, Interval(gt=0, lt=64)] | None]

        # pydantic conlist type
        con_list_int8: Annotated[list[None | Annotated[int, Interval(gt=-64, lt=64)]], Len(0)]
        con_list_uint8: Annotated[list[Optional[Annotated[int, Interval(gt=0, lt=64)]]], Len(0)]

    schema = model_to_nw_schema(ListModel, pipeline=auto_pipeline)
    expected = {
        "py_list_int8": nw.List(nw.Int8()),
        "py_list_uint8": nw.List(nw.UInt8()),
        "con_list_int8": nw.List(nw.Int8()),
        "con_list_uint8": nw.List(nw.UInt8()),
    }
    assert schema == expected
