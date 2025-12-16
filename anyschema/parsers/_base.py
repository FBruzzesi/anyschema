from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal, overload

from anyschema._utils import qualified_type_name
from anyschema.exceptions import UnavailablePipelineError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from narwhals.dtypes import DType

    from anyschema._anyschema import Field
    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType

__all__ = ("ParserPipeline", "ParserStep")


class ParserStep(ABC):
    """Abstract base class for parser steps that convert type annotations to Narwhals dtypes.

    This class provides a framework for parsing different types of type annotations
    and converting them into appropriate Narwhals data types. Each concrete parser
    implementation handles specific type patterns or annotation styles.

    Attributes:
        pipeline: Property to access the `ParserPipeline`, raises `UnavailablePipelineError` if not set.

    Raises:
        UnavailablePipelineError: When accessing pipeline before it's been set.
        TypeError: When setting pipeline with an object that's not a ParserPipeline instance.

    Note:
        Subclasses must implement the `parse` method to define their specific parsing logic.

    Examples:
        >>> from typing import get_origin, get_args
        >>> import narwhals as nw
        >>> from anyschema.parsers import ParserStep, PyTypeStep, make_pipeline
        >>> from anyschema.typing import FieldConstraints, FieldMetadata, FieldType
        >>>
        >>> class CustomType: ...
        >>> class CustomList[T]: ...
        >>>
        >>> class CustomParserStep(ParserStep):
        ...     def parse(
        ...         self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata
        ...     ) -> DType | None:
        ...         if input_type is CustomType:
        ...             return nw.String()
        ...
        ...         if get_origin(input_type) is CustomList:
        ...             inner = get_args(input_type)[0]
        ...             # Delegate to pipeline for recursion
        ...             inner_dtype = self.pipeline.parse(inner, constraints=constraints, metadata=metadata)
        ...             return nw.List(inner_dtype)
        ...
        ...         # Return None if we can't handle it
        ...         return None
        >>>
        >>> pipeline = make_pipeline(steps=[CustomParserStep(), PyTypeStep()])
        >>> pipeline.parse(CustomType, constraints=(), metadata={})
        String
        >>> pipeline.parse(CustomList[int], constraints=(), metadata={})
        List(Int64)
        >>> pipeline.parse(CustomList[str], constraints=(), metadata={})
        List(String)
    """

    _pipeline: ParserPipeline | None = None

    @property
    def pipeline(self) -> ParserPipeline:
        """Property that returns the parser chain instance.

        Returns:
            ParserPipeline: The parser chain object used for parsing operations.

        Raises:
            UnavailablePipelineError: If the parser chain has not been initialized
                (i.e., `_pipeline` is None).
        """
        if self._pipeline is None:
            msg = "`pipeline` is not set yet. You can set it by `step.pipeline = pipeline`"
            raise UnavailablePipelineError(msg)

        return self._pipeline

    @pipeline.setter
    def pipeline(self, pipeline: ParserPipeline) -> None:
        """Set the pipeline reference for this parser.

        Arguments:
            pipeline: The pipeline to set. Must be an instance of ParserPipeline.

        Raises:
            TypeError: If pipeline is not an instance of ParserPipeline.
        """
        if not isinstance(pipeline, ParserPipeline):
            msg = f"Expected `ParserPipeline` object, found {type(pipeline)}"
            raise TypeError(msg)

        self._pipeline = pipeline

    @abstractmethod
    def parse(self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata) -> DType | None:
        """Parse a type annotation into a Narwhals dtype.

        Arguments:
            input_type: The type to parse (e.g., int, str, list[int], etc.)
            constraints: Constraints associated with the type (e.g., Gt, Le from annotated-types)
            metadata: Custom metadata dictionary

        Returns:
            A Narwhals DType if the parser can handle this type, None otherwise.
        """
        ...

    def __repr__(self) -> str:
        return self.__class__.__name__


class ParserPipeline:
    """A pipeline of parser steps that tries each parser in sequence.

    This allows for composable parsing where multiple parsers can be tried until one successfully handles the type.

    Arguments:
        steps: Sequence of [`ParserStep`][anyschema.parsers.ParserStep]'s to use in the pipeline (in such order).
    """

    def __init__(self, steps: Sequence[ParserStep]) -> None:
        self.steps = tuple(steps)

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

    def parse_field(
        self,
        name: str,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> Field:
        """Parse a field specification into a Field object.

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
            A [`Field`][anyschema.Field] instance containing the parsed dtype and field-level metadata.

        Examples:
            >>> from anyschema.parsers import make_pipeline
            >>> pipeline = make_pipeline()
            >>> field = pipeline.parse_field("age", int, (), {})
            >>> field
            Field(name='age', dtype=Int64, nullable=False, unique=False, metadata={})

            With nullable=True metadata:

            >>> field = pipeline.parse_field("email", str, (), {"anyschema/nullable": True})
            >>> field.nullable
            True

            With Optional type (auto-detected as nullable):

            >>> from typing import Optional
            >>> field = pipeline.parse_field("email", Optional[str], (), {})
            >>> field.nullable
            True
        """
        from anyschema._anyschema import Field

        dtype = self.parse(input_type, constraints, metadata, strict=True)
        return Field(
            name=name,
            dtype=dtype,
            nullable=bool(metadata.get("anyschema/nullable", False)),
            unique=bool(metadata.get("anyschema/unique", False)),
            metadata={k: v for k, v in metadata.items() if not k.startswith("anyschema/")},
        )
