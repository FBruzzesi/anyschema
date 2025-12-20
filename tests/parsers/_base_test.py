# ruff: noqa: ARG002
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Sequence

import narwhals as nw
import pytest

from anyschema.exceptions import UnavailablePipelineError
from anyschema.parsers import AnnotatedStep, ParserPipeline, ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


class AlwaysNoneStep(ParserStep):
    def parse(  # pragma: no cover
        self,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> DType | None:
        return None


class StrStep(ParserStep):
    def parse(self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata) -> DType | None:
        return nw.String() if input_type is str else None


class Int32Step(ParserStep):
    def parse(self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata) -> DType | None:
        return nw.Int32() if input_type is int else None


class Int64Step(ParserStep):
    def parse(self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata) -> DType | None:
        return nw.Int64() if input_type is int else None


class MetadataAwareStep(ParserStep):
    def parse(self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata) -> DType | None:
        return nw.Int32() if input_type is int and constraints == ("meta1", "meta2") else None


def test_pipeline_not_set() -> None:
    step = AlwaysNoneStep()
    expected_msg = "`pipeline` is not set yet. You can set it by `step.pipeline = pipeline`"

    with pytest.raises(UnavailablePipelineError, match=expected_msg):
        _ = step.pipeline


def test_pipeline_set_valid() -> None:
    step = AlwaysNoneStep()
    pipeline = ParserPipeline([step])

    assert step.pipeline is pipeline


def test_pipeline_set_invalid_type() -> None:
    step = AlwaysNoneStep()

    with pytest.raises(TypeError, match="Expected `ParserPipeline` object, found"):
        step.pipeline = "not a pipeline"  # type: ignore[assignment]


def test_pipeline_setter_updates_correctly() -> None:
    step = AlwaysNoneStep()
    pipeline1 = ParserPipeline([step])

    # Trying to set pipeline again should raise (already set by ParserPipeline.__init__)
    with pytest.raises(TypeError, match="`pipeline` can only be set once"):
        step.pipeline = pipeline1  # Already set!

    # But cloning allows reuse
    cloned = step.clone()
    pipeline2 = ParserPipeline([cloned])
    assert cloned.pipeline is pipeline2


def test_pipeline_init_with_steps() -> None:
    steps: list[ParserStep] = [Int64Step(), StrStep()]
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

    result = pipeline.parse(input_type, (), {}, strict=False)
    assert result == expected


@pytest.mark.parametrize("input_type", [float, bool])
def test_pipeline_parse_strict(input_type: Any) -> None:
    pipeline = ParserPipeline([Int64Step(), StrStep()])

    with pytest.raises(NotImplementedError, match="No parser in the pipeline could handle type"):
        pipeline.parse(input_type, (), {}, strict=True)


def test_pipeline_parse_with_metadata() -> None:
    step = MetadataAwareStep()
    pipeline = ParserPipeline([step])

    r1 = pipeline.parse(int, constraints=("meta1", "meta2"), metadata={}, strict=True)
    assert r1 == nw.Int32()

    r2 = pipeline.parse(int, constraints=("meta1",), metadata={}, strict=False)
    assert r2 is None


@pytest.mark.parametrize(
    ("steps", "expected"),
    [((Int32Step(), Int64Step()), nw.Int32()), ((Int64Step(), Int32Step()), nw.Int64())],
)
def test_pipeline_parse_order_matters(steps: tuple[ParserStep, ...], expected: nw.dtypes.DType) -> None:
    pipeline = ParserPipeline(steps=steps)
    result = pipeline.parse(int, (), {}, strict=True)
    assert result == expected


def test_parser_step_repr() -> None:
    """Test that ParserStep has a proper __repr__ method."""
    step = Int64Step()
    assert repr(step) == "Int64Step"

    step2 = AlwaysNoneStep()
    assert repr(step2) == "AlwaysNoneStep"


def test_parser_step_clone() -> None:
    """Test that clone() creates a new step without pipeline reference."""
    step = Int64Step()
    pipeline = ParserPipeline([step])

    # Step should have pipeline set
    assert step.pipeline is pipeline

    # Clone should not have pipeline set
    cloned = step.clone()
    assert cloned is not step
    assert cloned._pipeline is None

    # Clone should work independently
    pipeline2 = ParserPipeline([cloned])
    assert cloned.pipeline is pipeline2
    assert step.pipeline is pipeline  # Original unchanged


def test_parser_step_clone_preserves_state() -> None:
    """Test that clone() preserves internal state of the step."""
    from anyschema.parsers import ForwardRefStep

    # ForwardRefStep has internal state (globalns)
    custom_globals = {"CustomType": str}
    step = ForwardRefStep(globalns=custom_globals)
    _ = ParserPipeline([step])  # Set pipeline on original

    cloned = step.clone()

    # Cloned step should have the same globalns
    assert cloned.globalns == step.globalns
    # But should be able to set a new pipeline
    pipeline2 = ParserPipeline([cloned])
    assert cloned.pipeline is pipeline2


@pytest.mark.parametrize(
    ("original_steps", "steps_to_add", "at_position", "expected"),
    [
        (
            (AnnotatedStep(), Int64Step(), StrStep()),
            Int32Step(),
            "auto",
            (AnnotatedStep, Int32Step, Int64Step, StrStep),
        ),
        (
            (AnnotatedStep(), StrStep()),
            (Int32Step(), Int64Step()),
            "auto",
            (AnnotatedStep, Int32Step, Int64Step, StrStep),
        ),
        (
            (Int64Step(), StrStep()),
            Int32Step(),
            "auto",
            (Int32Step, Int64Step, StrStep),
        ),
        (
            (Int64Step(), StrStep()),
            Int32Step(),
            1,
            (Int64Step, Int32Step, StrStep),
        ),
        (
            (Int64Step(), StrStep()),
            Int32Step(),
            100,
            (Int64Step, StrStep, Int32Step),
        ),
        (
            (Int64Step(), StrStep()),
            Int32Step(),
            -100,
            (Int32Step, Int64Step, StrStep),
        ),
    ],
)
def test_pipeline_with_steps(
    original_steps: tuple[ParserStep, ...],
    steps_to_add: ParserStep | Sequence[ParserStep],
    at_position: int | Literal["auto"],
    expected: tuple[type[ParserStep], ...],
) -> None:
    pipeline = ParserPipeline(original_steps)
    new_pipeline = pipeline.with_steps(steps_to_add, at_position=at_position)

    assert all(isinstance(step, step_type) for step, step_type in zip(new_pipeline.steps, expected, strict=True))


def test_pipeline_from_auto() -> None:
    pipeline = ParserPipeline.from_auto(Int32Step(), Int64Step())

    s1, s2 = pipeline.steps[3:5]
    assert isinstance(s1, Int32Step)
    assert isinstance(s2, Int64Step)


def test_from_auto_explicit_position() -> None:
    pipeline = ParserPipeline.from_auto(Int32Step(), at_position=0)
    assert isinstance(pipeline.steps[0], Int32Step)
