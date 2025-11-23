from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Optional

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
from anyschema.parsers.pydantic import PydanticTypeStep

if TYPE_CHECKING:
    from anyschema.typing import SpecType

PYDANTIC_PIPELINE_CLS_ORDER = (
    ForwardRefStep,
    UnionTypeStep,
    AnnotatedStep,
    AnnotatedTypesStep,
    PydanticTypeStep,
    PyTypeStep,
)
PYTHON_PIPELINE_CLS_ORDER = (ForwardRefStep, UnionTypeStep, AnnotatedStep, AnnotatedTypesStep, PyTypeStep)

PY_TYPE_STEP = PyTypeStep()


class Address(BaseModel):
    street: str
    city: str


class Person(BaseModel):
    name: str
    address: Address


@pytest.mark.parametrize(
    ("spec_type", "expected_steps"),
    [
        ("pydantic", PYDANTIC_PIPELINE_CLS_ORDER),
        ("python", PYTHON_PIPELINE_CLS_ORDER),
        (None, PYTHON_PIPELINE_CLS_ORDER),
    ],
)
def test_make_pipeline_auto(spec_type: SpecType, expected_steps: tuple[type[ParserStep], ...]) -> None:
    pipeline = make_pipeline("auto", spec_type=spec_type)
    assert isinstance(pipeline, ParserPipeline)
    assert len(pipeline.steps) == len(expected_steps)

    for _parser, _cls in zip(pipeline.steps, expected_steps, strict=True):
        assert isinstance(_parser, _cls)
        assert _parser.pipeline is pipeline


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


@pytest.mark.parametrize(
    ("pipeline1", "pipeline2"),
    [
        (_auto_pipeline(spec_type="pydantic"), _auto_pipeline(spec_type="pydantic")),
    ],
)
def test_caching(pipeline1: ParserPipeline, pipeline2: ParserPipeline) -> None:
    # Due to lru_cache, should be the same object
    assert pipeline1 is pipeline2

    pipeline3 = _auto_pipeline(spec_type="python")

    # Different parameters should create different pipelines
    assert pipeline1 is not pipeline3


@pytest.mark.parametrize(
    ("input_type", "spec_type", "expected"),
    [
        (int, "pydantic", nw.Int64()),
        (str, "pydantic", nw.String()),
        (list[int], "pydantic", nw.List(nw.Int64())),
        (Optional[int], "pydantic", nw.Int64()),
        (int, "python", nw.Int64()),
        (str, "python", nw.String()),
        (list[str], "python", nw.List(nw.String())),
        (Optional[float], "python", nw.Float64()),
        (Annotated[int, Gt(0)], "pydantic", nw.UInt64()),
        (PositiveInt, "pydantic", nw.UInt64()),
        (Optional[str], "python", nw.String()),
        (list[list[int]], "python", nw.List(nw.List(nw.Int64()))),
        (Optional[Annotated[int, Gt(0)]], "pydantic", nw.UInt64()),
        (Annotated[Optional[int], "metadata"], "pydantic", nw.Int64()),
        (Optional[list[int]], "pydantic", nw.List(nw.Int64())),
        (list[Optional[int]], "pydantic", nw.List(nw.Int64())),
    ],
)
def test_non_nested_parsing(input_type: type, spec_type: SpecType, expected: nw.dtypes.DType) -> None:
    pipeline = make_pipeline("auto", spec_type=spec_type)
    result = pipeline.parse(input_type)
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
def test_nested_parsing(input_type: type, expected: nw.dtypes.DType) -> None:
    pipeline = make_pipeline("auto", spec_type="pydantic")
    result = pipeline.parse(input_type)
    assert result == expected
