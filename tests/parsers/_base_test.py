# ruff: noqa: ARG002
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import narwhals as nw
import pytest

from anyschema.exceptions import UnavailablePipelineError
from anyschema.parsers import ParserPipeline, ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType


class AlwaysNoneStep(ParserStep):
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        return None


class StrStep(ParserStep):
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        return nw.String() if input_type is str else None


class Int32Step(ParserStep):
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        return nw.Int32() if input_type is int else None


class Int64Step(ParserStep):
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        return nw.Int64() if input_type is int else None


class MetadataAwareStep(ParserStep):
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        return nw.Int32() if input_type is int and metadata == ("meta1", "meta2") else None


def test_pipeline_not_set() -> None:
    step = AlwaysNoneStep()
    expected_msg = "`pipeline` is not set yet. You can set it by `step.pipeline = pipeline`"

    with pytest.raises(UnavailablePipelineError, match=expected_msg):
        _ = step.pipeline


def test_pipeline_set_valid() -> None:
    step = AlwaysNoneStep()
    pipeline = ParserPipeline([step])
    step.pipeline = pipeline

    assert step.pipeline is pipeline


def test_pipeline_set_invalid_type() -> None:
    step = AlwaysNoneStep()

    with pytest.raises(TypeError, match="Expected `ParserPipeline` object, found"):
        step.pipeline = "not a pipeline"  # type: ignore[assignment]


def test_pipeline_setter_updates_correctly() -> None:
    step = AlwaysNoneStep()
    pipeline1 = ParserPipeline([step])
    pipeline2 = ParserPipeline([step])

    step.pipeline = pipeline1
    assert step.pipeline is pipeline1

    step.pipeline = pipeline2
    assert step.pipeline is pipeline2


def test_pipeline_init_with_steps() -> None:
    int_step, str_step = Int64Step(), StrStep()
    steps = [int_step, str_step]
    pipeline = ParserPipeline(steps)

    assert len(pipeline.steps) == len(steps)
    assert pipeline.steps == tuple(steps)
    assert isinstance(pipeline.steps, tuple)

    # Modifying the original list shouldn't affect the pipeline
    no_step = AlwaysNoneStep()
    steps.append(no_step)
    assert len(pipeline.steps) < len(steps)


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (int, nw.Int64()),
        (str, nw.String()),
        (bool, None),
    ],
)
def test_pipeline_parse_non_strict(input_type: Any, expected: nw.dtypes.DType | None) -> None:
    pipeline = ParserPipeline([Int64Step(), StrStep()])

    result = pipeline.parse(input_type, strict=False)
    assert result == expected


@pytest.mark.parametrize("input_type", [float, bool])
def test_pipeline_parse_strict(input_type: Any) -> None:
    pipeline = ParserPipeline([Int64Step(), StrStep()])

    with pytest.raises(NotImplementedError, match="No parser in the pipeline could handle type"):
        pipeline.parse(input_type, strict=True)


def test_pipeline_parse_with_metadata() -> None:
    step = MetadataAwareStep()
    pipeline = ParserPipeline([step])

    result = pipeline.parse(int, metadata=("meta1", "meta2"), strict=True)
    assert result == nw.Int32()

    result = pipeline.parse(int, metadata=("meta1",), strict=False)
    assert result is None


@pytest.mark.parametrize(
    ("steps", "expected"),
    [((Int32Step(), Int64Step()), nw.Int32()), ((Int64Step(), Int32Step()), nw.Int64())],
)
def test_pipeline_parse_order_matters(steps: tuple[ParserStep, ...], expected: nw.dtypes.DType) -> None:
    pipeline = ParserPipeline(steps=steps)
    result = pipeline.parse(int, strict=True)
    assert result == expected
