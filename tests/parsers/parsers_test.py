from __future__ import annotations

from typing import Annotated, Optional

import narwhals as nw
import pytest
from annotated_types import Gt
from pydantic import BaseModel, PositiveInt

from anyschema.parsers import (
    AnnotatedStep,
    ForwardRefStep,
    ParserPipeline,
    ParserStep,
    PyTypeStep,
    UnionTypeStep,
    _auto_pipeline,
    make_pipeline,
)
from anyschema.parsers.annotated_types import AnnotatedTypesStep
from anyschema.parsers.attrs import AttrsTypeStep
from anyschema.parsers.pydantic import PydanticTypeStep
from anyschema.parsers.sqlalchemy import SQLAlchemyTypeStep

AUTO_PIPELINE_CLS_ORDER = (
    ForwardRefStep,
    UnionTypeStep,
    AnnotatedStep,
    AnnotatedTypesStep,
    AttrsTypeStep,
    PydanticTypeStep,
    SQLAlchemyTypeStep,
    PyTypeStep,
)

PY_TYPE_STEP = PyTypeStep()


class Address(BaseModel):
    street: str
    city: str


class Person(BaseModel):
    name: str
    address: Address


def test_make_pipeline_auto(auto_pipeline: ParserPipeline) -> None:
    assert isinstance(auto_pipeline, ParserPipeline)
    assert len(auto_pipeline.steps) == len(AUTO_PIPELINE_CLS_ORDER)

    for _parser, _cls in zip(auto_pipeline.steps, AUTO_PIPELINE_CLS_ORDER, strict=True):
        assert isinstance(_parser, _cls)
        assert _parser.pipeline is auto_pipeline


@pytest.mark.parametrize(
    "steps",
    [
        (PyTypeStep(),),
        (UnionTypeStep(), PyTypeStep()),
        (UnionTypeStep(), AnnotatedStep(), PyTypeStep()),
    ],
)
def test_make_pipeline_custom(steps: tuple[ParserStep, ...]) -> None:
    pipeline = make_pipeline(steps)
    assert isinstance(pipeline, ParserPipeline)
    assert len(pipeline.steps) == len(steps)

    for _pipeline_parser, _parser in zip(pipeline.steps, steps, strict=True):
        assert _parser is _pipeline_parser
        assert _parser.pipeline is pipeline


def test_caching() -> None:
    # Due to lru_cache, _auto_pipeline should return the same tuple object
    steps_1 = _auto_pipeline()
    steps_2 = _auto_pipeline()

    assert steps_1 is steps_2


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (int, nw.Int64()),
        (str, nw.String()),
        (list[int], nw.List(nw.Int64())),
        (Optional[int], nw.Int64()),
        (list[str], nw.List(nw.String())),
        (Optional[float], nw.Float64()),
        (Annotated[int, Gt(0)], nw.UInt64()),
        (PositiveInt, nw.UInt64()),
        (Optional[str], nw.String()),
        (list[list[int]], nw.List(nw.List(nw.Int64()))),
        (Optional[Annotated[int, Gt(0)]], nw.UInt64()),
        (Annotated[Optional[int], "meta"], nw.Int64()),
        (Optional[list[int]], nw.List(nw.Int64())),
        (list[Optional[int]], nw.List(nw.Int64())),
    ],
)
def test_non_nested_parsing(auto_pipeline: ParserPipeline, input_type: type, expected: nw.dtypes.DType) -> None:
    result = auto_pipeline.parse(input_type)
    assert result == expected


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (Address, nw.Struct([nw.Field(name="street", dtype=nw.String()), nw.Field(name="city", dtype=nw.String())])),
        (
            Person,
            nw.Struct(
                [
                    nw.Field(name="name", dtype=nw.String()),
                    nw.Field(
                        name="address",
                        dtype=nw.Struct(
                            [
                                nw.Field(name="street", dtype=nw.String()),
                                nw.Field(name="city", dtype=nw.String()),
                            ]
                        ),
                    ),
                ]
            ),
        ),
    ],
)
def test_nested_parsing(auto_pipeline: ParserPipeline, input_type: type, expected: nw.dtypes.DType) -> None:
    result = auto_pipeline.parse(input_type)
    assert result == expected
