from __future__ import annotations

from functools import cache
from itertools import chain
from types import GenericAlias
from typing import TYPE_CHECKING, Literal, cast, overload

from narwhals.dtypes import DType
from typing_extensions import Self

from anyschema._dependencies import ANNOTATED_TYPES_AVAILABLE, ATTRS_AVAILABLE, PYDANTIC_AVAILABLE, SQLALCHEMY_AVAILABLE
from anyschema._metadata import filter_anyschema_metadata, get_anyschema_value_by_key
from anyschema._utils import qualified_type_name
from anyschema.parsers._annotated import AnnotatedStep, field_contains_none
from anyschema.parsers._base import ParserStep
from anyschema.parsers._builtin import PyTypeStep
from anyschema.parsers._forward_ref import ForwardRefStep
from anyschema.parsers._union import UnionTypeStep
from anyschema.serde import deserialize_dtype

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Sequence

    from anyschema._anyschema import AnyField
    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType, IntoParserPipeline


class ParserPipeline:
    """A pipeline of parser steps that tries each parser in sequence.

    This allows for composable parsing where multiple parsers can be tried until one successfully handles the type.

    Arguments:
        steps: Control how parser steps are configured:

            - `"auto"` (default): Automatically select appropriate parser steps based on installed dependencies.
            - An iterable of [`ParserStep`][anyschema.parsers.ParserStep] instances: Create pipeline with these steps.

    Raises:
        TypeError: If a step is not a `ParserStep` instance.
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

        Raises:
            NotImplementedError: If no step can parse `input_type` and `strict=True`.
        """
        for step in self.steps:
            result = step.parse(input_type, constraints, metadata)
            if result is not None:
                return result

        if strict:
            # On Python 3.10 `set[int]` passes `isinstance(..., type)`.
            is_class = isinstance(input_type, type) and not isinstance(input_type, GenericAlias)
            type_name = repr(qualified_type_name(input_type)) if is_class else repr(input_type)
            msg = (
                f"No parser in the pipeline could handle type: {type_name}.\n"
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
        auto_steps = _auto_pipeline()
        insert_idx = cls._find_insert_index(steps=auto_steps, at_position=at_position)
        it = chain(
            auto_steps[:insert_idx],
            [steps] if isinstance(steps, ParserStep) else steps,
            more_steps,
            auto_steps[insert_idx:],
        )
        return cls(tuple(it))

    def parse_into_field(
        self,
        name: str,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> AnyField:
        """Parse a field specification into an [`AnyField`][anyschema.AnyField].

        Unlike [`parse`][anyschema.parsers.ParserPipeline.parse], it also sets the field-level information:
        nullability, uniqueness, description and custom metadata.

        `nullable` is the metadata value if it is set and not `None`, read after parsing so a custom step can set it.
        Otherwise the field is nullable when its field-level type contains `None`, with or without a `dtype` override:
        `T | None` and `Literal[..., None]` are nullable, `list[T | None]` is not. Forward references are resolved with
        the pipeline's `ForwardRefStep`.

        Arguments:
            name: The name of the field.
            input_type: The type to parse.
            constraints: Constraints associated with the type.
            metadata: The field metadata. It is not modified, so one dict may be shared across fields.

        Returns:
            The parsed field.

        Examples:
            >>> from anyschema.parsers import make_pipeline
            >>> pipeline = make_pipeline()
            >>> field = pipeline.parse_into_field("age", int, (), {})
            >>> field
            AnyField(name='age', dtype=Int64, nullable=False, unique=False, description=None, metadata={})

            >>> from typing import Optional
            >>> pipeline.parse_into_field("email", Optional[str], (), {}).nullable
            True
            >>> pipeline.parse_into_field("email", Optional[str], (), {"anyschema": {"nullable": False}}).nullable
            False
            >>> pipeline.parse_into_field("tags", list[Optional[str]], (), {}).nullable
            False
        """
        from anyschema._anyschema import AnyField

        # Custom steps may write into `metadata` (e.g. `nullable`), so work on a copy.
        metadata = dict(metadata)
        if (into_dtype := get_anyschema_value_by_key(metadata, key="dtype")) is not None:
            if isinstance(into_dtype, DType):
                dtype = into_dtype
            elif isinstance(into_dtype, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                dtype = deserialize_dtype(into_dtype=into_dtype)
            else:
                msg = (
                    f"Expected `dtype` value to be of type `narwhals.dtypes.DType` or `str`, \n"
                    f"found '{qualified_type_name(into_dtype)}' instead."
                )
                raise TypeError(msg)
        else:
            dtype = self.parse(input_type, constraints, metadata, strict=True)

        nullable = get_anyschema_value_by_key(metadata, key="nullable")
        if nullable is None:
            forward_ref_step = next((step for step in self.steps if isinstance(step, ForwardRefStep)), None)
            nullable = field_contains_none(input_type, forward_ref_step.resolve if forward_ref_step else None)
        return AnyField(
            name=name,
            dtype=dtype,
            nullable=nullable,
            unique=get_anyschema_value_by_key(metadata, key="unique", default=False),
            description=get_anyschema_value_by_key(metadata, key="description"),
            metadata=filter_anyschema_metadata(metadata),
        )


def make_pipeline(steps: ParserPipeline | IntoParserPipeline = "auto") -> ParserPipeline:
    """Create a [`ParserPipeline`][anyschema.parsers.ParserPipeline] with the specified steps.

    Arguments:
        steps: Control how parser steps are configured:

            - `"auto"` (default): Automatically select appropriate parser steps based on installed dependencies.
            - A [`ParserPipeline`][anyschema.parsers.ParserPipeline] instance: Return the pipeline as-is.
            - An iterable of [`ParserStep`][anyschema.parsers.ParserStep] instances: Create pipeline with these steps.

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
        TypeError: If a step is not a `ParserStep` instance.
    """
    return steps if isinstance(steps, ParserPipeline) else ParserPipeline(steps)


@cache
def shared_auto_pipeline() -> ParserPipeline:
    """Return the "auto" pipeline that `AnySchema` uses by default, built once and never handed to users.

    Steps hold no mutable state and `parse_into_field` copies the metadata, so threads can share it.
    """
    return ParserPipeline("auto")


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


def _ensure_steps(steps: Iterable[object]) -> tuple[ParserStep, ...]:
    """Return `steps` as a tuple, or raise a `TypeError` naming every step that is not a `ParserStep`."""
    steps = tuple(steps)  # Materialize first: the check below would exhaust a generator.
    if invalid_names := [qualified_type_name(step) for step in steps if not isinstance(step, ParserStep)]:
        msg = f"Expected a sequence of `ParserStep` instances, found {', '.join(invalid_names)}"
        raise TypeError(msg)
    return cast("tuple[ParserStep, ...]", steps)
