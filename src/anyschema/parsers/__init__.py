from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from anyschema._dependencies import ANNOTATED_TYPES_AVAILABLE
from anyschema.parsers._annotated import AnnotatedStep
from anyschema.parsers._base import ParserPipeline, ParserStep
from anyschema.parsers._builtin import PyTypeStep
from anyschema.parsers._forward_ref import ForwardRefStep
from anyschema.parsers._union import UnionTypeStep

if TYPE_CHECKING:
    from collections.abc import Sequence

    from anyschema.typing import IntoParserPipeline, SpecType

__all__ = (
    "AnnotatedStep",
    "ForwardRefStep",
    "ParserPipeline",
    "ParserStep",
    "PyTypeStep",
    "UnionTypeStep",
    "make_pipeline",
)


def make_pipeline(steps: IntoParserPipeline = "auto", *, spec_type: SpecType = None) -> ParserPipeline:
    """Create a parser pipeline with the specified steps.

    Arguments:
        steps: steps to use in the ParserPipeline. If "auto" then the sequence is automatically populated based on
            the spec_type.
        spec_type: The type of model being parsed ("pydantic" or "python"). Only used when parsers="auto".

    Returns:
        A ParserPipeline instance with the configured parsers.
    """
    steps = _auto_pipeline(spec_type) if steps == "auto" else tuple(steps)
    pipeline = ParserPipeline(steps)

    # Wire up the pipeline reference for parsers that need it
    # TODO(FBruzzesi): Is there a better way to achieve this?
    for step in steps:
        step.pipeline = pipeline

    return pipeline


@lru_cache(maxsize=16)
def _auto_pipeline(spec_type: SpecType) -> Sequence[ParserStep]:
    """Create a parser chain with automatically selected parsers.

    Arguments:
        spec_type: The type of model being parsed.

    Returns:
        A ParserPipeline instance with automatically selected parsers.
    """
    # Create parser instances without chain reference (yet)
    forward_ref_step = ForwardRefStep()
    union_step = UnionTypeStep()
    annotated_step = AnnotatedStep()
    python_step = PyTypeStep()

    # Order matters! More specific steps should come first:
    # 1. ForwardRefStep - resolves ForwardRef to actual types (MUST be first!)
    # 2. UnionTypeStep - handles Union/Optional and extracts the real type
    # 3. AnnotatedStep - extracts typing.Annotated and its metadata
    # 4. AnnotatedTypesStep - refines types based on metadata (e.g., int with constraints)
    # 5. PydanticTypeStep - handles Pydantic-specific types (if pydantic model)
    # 6. PyTypeStep - handles basic Python types (fallback)
    steps: Sequence[ParserStep]
    if spec_type == "pydantic":
        from anyschema.parsers.annotated_types import AnnotatedTypesStep
        from anyschema.parsers.pydantic import PydanticTypeStep

        annotated_types_step = AnnotatedTypesStep()
        pydantic_step = PydanticTypeStep()

        steps = (
            forward_ref_step,
            union_step,
            annotated_step,
            annotated_types_step,
            pydantic_step,
            python_step,
        )
    elif ANNOTATED_TYPES_AVAILABLE:
        from anyschema.parsers.annotated_types import AnnotatedTypesStep

        annotated_types_step = AnnotatedTypesStep()
        steps = (forward_ref_step, union_step, annotated_step, annotated_types_step, python_step)
    else:  # pragma: no cover
        steps = (forward_ref_step, union_step, annotated_step, python_step)
    return steps
