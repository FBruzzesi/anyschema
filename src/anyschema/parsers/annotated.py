from __future__ import annotations

from types import GenericAlias
from typing import TYPE_CHECKING, Annotated, _GenericAlias, get_args, get_origin  # type: ignore[attr-defined]

from anyschema.parsers.base import TypeParser

if TYPE_CHECKING:
    from narwhals.dtypes import DType


class AnnotatedParser(TypeParser):
    """Parser for typing.Annotated types.

    Handles:
    - Annotated[T, metadata...] - extracts the type and metadata for further parsing
    """

    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        """Parse Annotated types by extracting the base type and metadata.

        Arguments:
            input_type: The type to parse.
            metadata: Optional metadata associated with the type.

        Returns:
            A Narwhals DType by extracting the base type and delegating to the chain.
        """
        # Handle Annotated types from typing module
        if isinstance(input_type, (_GenericAlias, GenericAlias)):
            origin = get_origin(input_type)
            if origin is Annotated:
                args = get_args(input_type)
                if args:
                    # First arg is the actual type, rest are metadata
                    base_type = args[0]
                    extra_metadata = args[1:] if len(args) > 1 else ()

                    # Combine existing metadata with extracted metadata
                    combined_metadata = metadata + extra_metadata

                    # Recursively parse the base type with combined metadata
                    return self.parser_chain.parse(base_type, combined_metadata, strict=True)

        return None


__all__ = ("AnnotatedParser",)
