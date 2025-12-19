from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Literal, overload

from typing_extensions import TypeIs

from anyschema._dependencies import ANNOTATED_TYPES_AVAILABLE, ATTRS_AVAILABLE, PYDANTIC_AVAILABLE, SQLALCHEMY_AVAILABLE
from anyschema._utils import qualified_type_name
from anyschema.parsers._annotated import AnnotatedStep
from anyschema.parsers._base import ParserStep
from anyschema.parsers._builtin import PyTypeStep
from anyschema.parsers._forward_ref import ForwardRefStep
from anyschema.parsers._union import UnionTypeStep

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from anyschema._anyschema import AnyField
    from anyschema.typing import IntoParserPipeline


if TYPE_CHECKING:
    from collections.abc import Sequence

    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


class ParserPipeline:
    """A pipeline of parser steps that tries each parser in sequence.

    This allows for composable parsing where multiple parsers can be tried until one successfully handles the type.

    Arguments:
        steps: Sequence of [`ParserStep`][anyschema.parsers.ParserStep]'s to use in the pipeline (in such order).
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

    def parse_into_field(
        self,
        name: str,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> AnyField:
        """Parse a field specification into a AnyField object.

        This is the recommended method for parsing field specifications at the top level.
        It wraps the DType parsing with additional field-level information like nullability,
        uniqueness, and custom metadata.

        The metadata dictionary is populated during parsing (e.g., `UnionTypeStep` sets
        `anyschema/nullable` for `Optional[T]` types), ensuring that forward references
        are properly evaluated and avoiding code duplication.

        Arguments:
            name: The name of the field.
            input_type: The type to parse.
            constraints: Constraints associated with the type.
            metadata: Custom metadata dictionary. This dictionary may be modified during
                parsing to add field-level metadata like `anyschema/nullable`.

        Returns:
            A [`AnyField`][anyschema.AnyField] instance containing the parsed dtype and field-level metadata.

        Examples:
            >>> from anyschema.parsers import make_pipeline
            >>> pipeline = make_pipeline()
            >>> field = pipeline.parse_into_field("age", int, (), {})
            >>> field
            AnyField(name='age', dtype=Int64, nullable=False, unique=False, description=None, metadata={})

            With nullable=True metadata:

            >>> field = pipeline.parse_into_field("email", str, (), {"anyschema/nullable": True})
            >>> field.nullable
            True

            With Optional type (auto-detected as nullable):

            >>> from typing import Optional
            >>> field = pipeline.parse_into_field("email", Optional[str], (), {})
            >>> field.nullable
            True
        """
        from anyschema._anyschema import AnyField

        dtype = self.parse(input_type, constraints, metadata, strict=True)

        return AnyField(
            name=name,
            dtype=dtype,
            nullable=metadata.get("anyschema/nullable", False),
            unique=metadata.get("anyschema/unique", False),
            description=metadata.get("anyschema/description"),
            metadata={k: v for k, v in metadata.items() if not k.startswith("anyschema/")},
        )


def make_pipeline(steps: IntoParserPipeline = "auto") -> ParserPipeline:
    """Create a [`ParserPipeline`][anyschema.parsers.ParserPipeline] with the specified steps.

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
    return ParserPipeline(steps)


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
