from __future__ import annotations

from itertools import chain
from typing import TYPE_CHECKING, Literal, overload

from typing_extensions import Self, TypeIs

from anyschema._dependencies import ANNOTATED_TYPES_AVAILABLE, ATTRS_AVAILABLE, PYDANTIC_AVAILABLE, SQLALCHEMY_AVAILABLE
from anyschema._utils import qualified_type_name
from anyschema.parsers._annotated import AnnotatedStep
from anyschema.parsers._base import ParserStep
from anyschema.parsers._builtin import PyTypeStep
from anyschema.parsers._forward_ref import ForwardRefStep
from anyschema.parsers._union import UnionTypeStep

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType, IntoParserPipeline


class ParserPipeline:
    """A pipeline of parser steps that tries each parser in sequence.

    This allows for composable parsing where multiple parsers can be tried until one successfully handles the type.

    Arguments:
        steps: Control how parser steps are configured:

            - `"auto"` (default): Automatically select appropriate parser steps based on installed dependencies.
            - A [`ParserPipeline`][anyschema.parsers.ParserPipeline] instance: Use the pipeline as-is.
            - A sequence of [`ParserStep`][anyschema.parsers.ParserStep] instances: Create pipeline with these steps.

    Raises:
        TypeError: If the steps are not a sequence of `ParserStep` instances or a `ParserPipeline`.
    """

    steps: Sequence[ParserStep]

    def __init__(self, steps: IntoParserPipeline = "auto") -> None:
        self.steps = _auto_pipeline() if steps == "auto" else _ensure_steps(steps)
        for step in self.steps:
            step.pipeline = self

    @overload
    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
        *,
        strict: Literal[True] = True,
    ) -> DType: ...
    @overload
    def parse(
        self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata, *, strict: Literal[False]
    ) -> DType | None: ...

    def parse(
        self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata, *, strict: bool = True
    ) -> DType | None:
        """Try each parser in sequence until one succeeds.

        Arguments:
            input_type: The type to parse.
            constraints: Constraints associated with the type.
            metadata: Custom metadata dictionary.
            strict: Whether or not to raise if unable to parse `input_type`.

        Returns:
            A Narwhals DType from the first successful parser, or None if no parser succeeded and `strict=False`.
        """
        for step in self.steps:
            result = step.parse(input_type, constraints, metadata)
            if result is not None:
                return result

        if strict:
            msg = (
                f"No parser in the pipeline could handle type: '{qualified_type_name(input_type)}'.\n"
                f"Please consider opening a feature request https://github.com/FBruzzesi/anyschema/issues"
            )
            raise NotImplementedError(msg)
        return None

    @classmethod
    def _find_auto_position(cls, steps: Sequence[ParserStep]) -> int:
        """Find the best automatic insertion position for a custom parser step.

        Tries to insert after preprocessing steps in order of preference: AnnotatedStep, UnionTypeStep, ForwardRefStep.
        If none are found, returns 0 (insert at beginning).

        Returns:
            The index position where a new step should be inserted.
        """
        target_types = (AnnotatedStep, UnionTypeStep, ForwardRefStep)
        for step_type in target_types:
            for idx, existing_step in enumerate(steps):
                if isinstance(existing_step, step_type):
                    return idx + 1
        return 0

    @classmethod
    def _find_insert_index(cls, steps: Sequence[ParserStep], at_position: Literal["auto"] | int) -> int:
        if at_position == "auto":
            insert_idx = cls._find_auto_position(steps)
        else:
            n_steps = len(steps)
            raw_idx = at_position if at_position >= 0 else n_steps + at_position
            insert_idx = max(0, min(raw_idx, n_steps))  # Clamp to [0, n_steps]
        return insert_idx

    def with_steps(
        self,
        steps: ParserStep | Sequence[ParserStep],
        *more_steps: ParserStep,
        at_position: int | Literal["auto"] = "auto",
    ) -> Self:
        """Create a new pipeline with additional parser step(s) inserted at the specified position.

        Arguments:
            steps: `ParserStep`(s) to add to the pipeline.
            *more_steps: Additional `ParserStep`(s) to add, specified as positional arguments.
            at_position: Position where to insert the step(s). Options:

                - An integer index (can be negative for counting from the end).
                - `"auto"` (default): Automatically determines the "best" position.
                    The step(s) will be inserted after the last preprocessing step found (trying `AnnotatedStep`,
                    `UnionTypeStep`, `ForwardRefStep` in that order), ensuring custom parsers run after type
                    preprocessing but before library-specific or fallback parsers.
                    If no preprocessing steps are found, inserts at the beginning.

        Returns:
            A new `ParserPipeline` instance with the step(s) added at the specified position.

        Examples:
            >>> from anyschema.parsers import ParserPipeline, ParserStep
            >>> import narwhals as nw
            >>> from anyschema.typing import FieldConstraints, FieldMetadata, FieldType
            >>>
            >>> class CustomType: ...
            >>>
            >>> class CustomParserStep(ParserStep):
            ...     def parse(
            ...         self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata
            ...     ) -> nw.DType | None:
            ...         if input_type is CustomType:
            ...             return nw.String()
            ...         return None
            >>>
            >>> pipeline = ParserPipeline("auto")  # Start with auto pipeline
            >>>
            >>> # Add single custom step
            >>> custom_pipeline = pipeline.with_steps(CustomParserStep())
            >>>
            >>> # Add multiple custom steps at once
            >>> custom_pipeline = pipeline.with_steps([CustomParserStep(), CustomParserStep()])
            >>>
            >>> # Or add at specific position
            >>> custom_pipeline = pipeline.with_steps(CustomParserStep(), at_position=0)
            >>>
            >>> custom_pipeline.parse(CustomType, constraints=(), metadata={})
            String
        """
        insert_idx = self._find_insert_index(steps=self.steps, at_position=at_position)
        # Clone existing steps to reset their pipeline references
        it = chain(
            (step.clone() for step in self.steps[:insert_idx]),
            [steps] if isinstance(steps, ParserStep) else steps,
            more_steps,
            (step.clone() for step in self.steps[insert_idx:]),
        )
        return self.__class__(tuple(it))

    @classmethod
    def from_auto(
        cls,
        steps: ParserStep | Sequence[ParserStep],
        *more_steps: ParserStep,
        at_position: int | Literal["auto"] = "auto",
    ) -> Self:
        """Create an auto pipeline with custom steps efficiently (no copying needed).

        Tip:
            This is the most efficient way to create a pipeline with custom steps when starting from
            the auto configuration, as it doesn't need to copy the auto pipeline's steps.

        Arguments:
            steps: `ParserStep`(s) to add to the auto pipeline.
            *more_steps: Additional `ParserStep`(s) to add, specified as positional arguments.
            at_position: Position where to insert the step(s). Options:

                - An integer index (can be negative for counting from the end).
                - `"auto"` (default): Automatically determines the "best" position.
                    The step(s) will be inserted after the last preprocessing step found.

        Returns:
            A new `ParserPipeline` instance with the auto steps and custom steps.

        Examples:
            >>> from anyschema.parsers import ParserPipeline, ParserStep
            >>> import narwhals as nw
            >>> from anyschema.typing import FieldConstraints, FieldMetadata, FieldType
            >>>
            >>> class CustomType: ...
            >>>
            >>> class CustomParserStep(ParserStep):
            ...     def parse(
            ...         self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata
            ...     ) -> nw.DType | None:
            ...         return nw.String() if input_type is CustomType else None
            >>>
            >>> pipeline = ParserPipeline.from_auto(CustomParserStep())
            >>>
            >>> # Add multiple custom steps
            >>> pipeline = ParserPipeline.from_auto(CustomParserStep(), CustomParserStep())
            >>>
            >>> pipeline.parse(CustomType, constraints=(), metadata={})
            String
        """
        auto_steps = tuple(_auto_pipeline())
        insert_idx = cls._find_insert_index(steps=auto_steps, at_position=at_position)
        it = chain(
            auto_steps[:insert_idx],
            [steps] if isinstance(steps, ParserStep) else steps,
            more_steps,
            auto_steps[insert_idx:],
        )
        return cls(tuple(it))


def make_pipeline(steps: IntoParserPipeline = "auto") -> ParserPipeline:
    """Create a [`ParserPipeline`][anyschema.parsers.ParserPipeline] with the specified steps.

    Arguments:
        steps: Control how parser steps are configured:

            - `"auto"` (default): Automatically select appropriate parser steps based on installed dependencies.
            - A [`ParserPipeline`][anyschema.parsers.ParserPipeline] instance: Return the pipeline as-is.
            - A sequence of [`ParserStep`][anyschema.parsers.ParserStep] instances: Create pipeline with these steps.

    Returns:
        A [`ParserPipeline`][anyschema.parsers.ParserPipeline] instance with the configured steps.

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
        TypeError: If the steps are not a sequence of `ParserStep` instances or a `ParserPipeline`.
    """
    return ParserPipeline(steps)


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


def _is_parser_step(obj: object) -> TypeIs[ParserStep]:
    return isinstance(obj, ParserStep)


def _is_all_parser_steps(steps: Sequence[object]) -> TypeIs[Sequence[ParserStep]]:
    return all(_is_parser_step(step) for step in steps)


def _ensure_steps(steps: Sequence[object]) -> Sequence[ParserStep]:
    """Ensure that all steps in a sequence are ParserStep instances before returning them.

    Arguments:
        steps: A sequence of objects that should be ParserStep instances.

    Returns:
        A tuple of ParserStep instances if all steps are valid.

    Raises:
        TypeError: If any step in the sequence is not a ParserStep instance.
            The error message includes the qualified type names of invalid steps.
    """
    if _is_all_parser_steps(steps):
        return tuple(steps)

    not_step_types = tuple(not isinstance(step, ParserStep) for step in steps)
    bad_steps = tuple(
        qualified_type_name(type(step))
        for step, not_step_type in zip(steps, not_step_types, strict=False)
        if not_step_type
    )
    msg = f"Expected a sequence of `ParserStep` instances, found {', '.join(bad_steps)}"
    raise TypeError(msg)
