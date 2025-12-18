# mypy: disable-error-code="valid-type"
# pyright: reportInvalidTypeForm=false

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import narwhals as nw
from pydantic import BaseModel, conint, conlist

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
        con_list: conlist(int, min_length=2)
        con_list_optional: conlist(str, max_length=6) | None
        con_list_or_none: conlist(float) | None
        none_or_con_list: None | conlist(bool)

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
        con_list_optional: conlist(Optional[int], min_length=2)  # pyright: ignore[reportArgumentType]
        con_list_or_none: conlist(str | None, max_length=6)  # pyright: ignore[reportArgumentType]
        none_or_con_list: conlist(None | float)  # pyright: ignore[reportArgumentType]

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
        con_list_optional_optional: conlist(Optional[int], min_length=2) | None  # pyright: ignore[reportArgumentType]
        con_list_optional_none: conlist(str | None, max_length=6) | None  # pyright: ignore[reportArgumentType]
        con_list_none_optional: conlist(Optional[float]) | None  # pyright: ignore[reportArgumentType]
        con_list_none_none: conlist(None | bool) | None  # pyright: ignore[reportArgumentType]

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
        py_list_int8: list[conint(gt=-64, lt=64)] | None
        py_list_uint8: list[conint(gt=0, lt=64) | None]

        # pydantic conlist type
        con_list_int8: conlist(None | conint(gt=-64, lt=64))  # pyright: ignore[reportArgumentType]
        con_list_uint8: conlist(Optional[conint(gt=0, lt=64)])  # pyright: ignore[reportArgumentType]

    schema = model_to_nw_schema(ListModel, pipeline=auto_pipeline)
    expected = {
        "py_list_int8": nw.List(nw.Int8()),
        "py_list_uint8": nw.List(nw.UInt8()),
        "con_list_int8": nw.List(nw.Int8()),
        "con_list_uint8": nw.List(nw.UInt8()),
    }
    assert schema == expected
