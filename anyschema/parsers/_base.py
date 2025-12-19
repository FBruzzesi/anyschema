from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from anyschema.exceptions import UnavailablePipelineError

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.parsers._pipeline import ParserPipeline
    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType

__all__ = ("ParserStep",)


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
        from anyschema.parsers._pipeline import ParserPipeline

        if not isinstance(pipeline, ParserPipeline):  # pyright: ignore[reportUnnecessaryIsInstance]
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
