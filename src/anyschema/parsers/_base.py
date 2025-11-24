from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Literal, overload

from anyschema._utils import qualified_type_name
from anyschema.exceptions import UnavailablePipelineError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from narwhals.dtypes import DType

__all__ = ("ParserPipeline", "ParserStep")


class ParserStep(ABC):
    """Abstract base class for parser steps that convert type annotations to Narwhals dtypes.

    This class provides a framework for parsing different types of type annotations
    and converting them into appropriate Narwhals data types. Each concrete parser
    implementation handles specific type patterns or annotation styles.

    Attributes:
        pipeline: Property to access the `ParserPipeline`, raises `UnavailablePipelineError`
            if not set.

    Raises:
        UnavailablePipelineError: When accessing pipeline before it's been set.
        TypeError: When setting pipeline with an object that's not a ParserPipeline instance.

    Note:
        Subclasses must implement the `parse` method to define their specific parsing logic.

    Examples:
        >>> from typing import get_origin, get_args
        >>> import narwhals as nw
        >>> from anyschema.parsers import ParserStep, PyTypeStep, make_pipeline
        >>>
        >>> class CustomType: ...
        >>> class CustomList[T]: ...
        >>>
        >>> class CustomParserStep(ParserStep):
        ...     def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        ...         if input_type is CustomType:
        ...             return nw.String()
        ...
        ...         if get_origin(input_type) is CustomList:
        ...             inner = get_args(input_type)[0]
        ...             # Delegate to pipeline for recursion
        ...             inner_dtype = self.pipeline.parse(inner, metadata=metadata)
        ...             return nw.List(inner_dtype)
        ...
        ...         # Return None if we can't handle it
        ...         return None
        >>>
        >>> pipeline = make_pipeline(steps=[CustomParserStep(), PyTypeStep()])
        >>> pipeline.parse(CustomType)
        String
        >>> pipeline.parse(CustomList[int])
        List(Int64)
        >>> pipeline.parse(CustomList[str])
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
    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        """Parse a type annotation into a Narwhals dtype.

        Arguments:
            input_type: The type to parse (e.g., int, str, list[int], etc.)
            metadata: Optional metadata associated with the type (e.g., constraints)

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
    def parse(self, input_type: Any, metadata: tuple = (), *, strict: Literal[True] = True) -> DType: ...
    @overload
    def parse(self, input_type: Any, metadata: tuple = (), *, strict: Literal[False]) -> DType | None: ...

    def parse(self, input_type: Any, metadata: tuple = (), *, strict: bool = True) -> DType | None:
        """Try each parser in sequence until one succeeds.

        Arguments:
            input_type: The type to parse.
            metadata: Optional metadata associated with the type.
            strict: Whether or not to raise if unable to parse `input_type`.

        Returns:
            A Narwhals DType from the first successful parser, or None if no parser succeeded and `strict=False`.
        """
        for step in self.steps:
            result = step.parse(input_type, metadata)
            if result is not None:
                return result

        if strict:
            msg = (
                f"No parser in the pipeline could handle type: {qualified_type_name(input_type)}.\n"
                f"Please consider reporting a feature request https://github.com/FBruzzesi/anyschema/issues"
            )
            raise NotImplementedError(msg)
        return None
