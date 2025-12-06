from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from anyschema._dependencies import ANNOTATED_TYPES_AVAILABLE, ATTRS_AVAILABLE, PYDANTIC_AVAILABLE, SQLALCHEMY_AVAILABLE
from anyschema._utils import qualified_type_name
from anyschema.parsers._annotated import AnnotatedStep
from anyschema.parsers._base import ParserPipeline, ParserStep
from anyschema.parsers._builtin import PyTypeStep
from anyschema.parsers._forward_ref import ForwardRefStep
from anyschema.parsers._union import UnionTypeStep

if TYPE_CHECKING:
    from collections.abc import Generator

    from anyschema.typing import IntoParserPipeline

__all__ = (
    "AnnotatedStep",
    "ForwardRefStep",
    "ParserPipeline",
    "ParserStep",
    "PyTypeStep",
    "UnionTypeStep",
    "make_pipeline",
)


def make_pipeline(steps: IntoParserPipeline = "auto") -> ParserPipeline:
    """Create a [`ParserPipeline`][anyschema.parsers.ParserPipeline] with the specified steps and associates the
    pipeline to each step.

    Tip:
        This is the recommended way to create a parser pipeline.

    Arguments:
        steps: steps to use in the ParserPipeline. If "auto" then the sequence is automatically populated based on
            the available dependencies.

    Returns:
        A ParserPipeline instance with the configured parsers.

    Examples:
        >>> from anyschema.parsers import make_pipeline
        >>> from anyschema.parsers import PyTypeStep, UnionTypeStep, AnnotatedStep
        >>>
        >>> pipeline = make_pipeline(steps=[UnionTypeStep(), AnnotatedStep(), PyTypeStep()])
        >>> print(pipeline.steps)
        (UnionTypeStep, AnnotatedStep, PyTypeStep)

        >>> pipeline = make_pipeline(steps="auto")
        >>> print(pipeline.steps)  # doctest: +ELLIPSIS
        (ForwardRefStep, UnionTypeStep, ..., PydanticTypeStep, SQLAlchemyTypeStep, PyTypeStep)

    Raises:
        TypeError: If the steps are not a sequence of `ParserStep` instances.
    """
    if steps == "auto":
        steps = _auto_pipeline()
    else:
        steps = tuple(steps)
        if any(not_step_types := tuple(not isinstance(step, ParserStep) for step in steps)):
            bad_steps = tuple(
                qualified_type_name(type(step))
                for step, not_step_type in zip(steps, not_step_types, strict=False)
                if not_step_type
            )
            msg = f"Expected a sequence of `ParserStep` instances, found {', '.join(bad_steps)}"
            raise TypeError(msg)

    pipeline = ParserPipeline(steps)

    # Wire up the pipeline reference for parsers that need it
    # TODO(FBruzzesi): Is there a better way to achieve this?
    for step in steps:
        step.pipeline = pipeline

    return pipeline


@lru_cache(maxsize=1)
def _auto_pipeline() -> tuple[ParserStep, ...]:
    """Create a parser chain with automatically selected parsers.

    Returns:
        A `ParserPipeline` instance with automatically selected parsers.
    """

    def _generate_steps() -> Generator[ParserStep, None, None]:
        # Order matters! More specific steps should come first:

        # 1. ForwardRefStep - resolves ForwardRef to actual types (MUST be first!)
        yield ForwardRefStep()

        # 2. UnionTypeStep - handles Union/Optional and extracts the real type
        yield UnionTypeStep()

        # 3. AnnotatedStep - extracts typing.Annotated and its metadata
        yield AnnotatedStep()

        # 4. AnnotatedTypesStep - refines types based on metadata (e.g., int with constraints)
        #   (if annotated_types is available)
        if ANNOTATED_TYPES_AVAILABLE:
            from anyschema.parsers.annotated_types import AnnotatedTypesStep

            yield AnnotatedTypesStep()

        # 5. AttrsTypeStep - handles attrs-specific types (if attrs is available)
        if ATTRS_AVAILABLE:
            from anyschema.parsers.attrs import AttrsTypeStep

            yield AttrsTypeStep()

        # 6. PydanticTypeStep - handles Pydantic-specific types (if pydantic model)
        #   (if pydantic is available)
        if PYDANTIC_AVAILABLE:
            from anyschema.parsers.pydantic import PydanticTypeStep

            yield PydanticTypeStep()

        # 7. SQLAlchemyTypeStep - handles SQLAlchemy-specific types (if sqlalchemy is available)
        if SQLALCHEMY_AVAILABLE:
            from anyschema.parsers.sqlalchemy import SQLAlchemyTypeStep

            yield SQLAlchemyTypeStep()

        # 8. PyTypeStep - handles basic Python types (fallback)
        yield PyTypeStep()

    return tuple(_generate_steps())
