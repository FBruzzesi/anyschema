from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, get_args, get_origin

from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType


class AnnotatedStep(ParserStep):
    """Parser for `typing.Annotated` types.

    Handles:

    - `Annotated[T, metadata...]` - extracts the type and metadata for further parsing
    """

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        """Parse Annotated types by extracting the base type and metadata.

        Arguments:
            input_type: The type to parse.
            metadata: Optional metadata associated with the type.

        Returns:
            A Narwhals DType by extracting the base type and delegating to the chain.
        """
        if get_origin(input_type) is Annotated and (args := get_args(input_type)) is not None:
            base_type, *extra_metadata = args
            return self.pipeline.parse(base_type, (*metadata, *extra_metadata), strict=True)

        return None
