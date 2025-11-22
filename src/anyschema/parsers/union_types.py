from __future__ import annotations

from types import GenericAlias, NoneType, UnionType
from typing import TYPE_CHECKING, Any, Union, _GenericAlias, get_args, get_origin  # type: ignore[attr-defined]

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers.base import TypeParser

if TYPE_CHECKING:
    from narwhals.dtypes import DType


class UnionTypeParser(TypeParser):
    """Parser for Union types including Optional (T | None).

    Handles:
    - Union[T, None] / T | None / Optional[T] (Optional types)
    - Extracts the non-None type and its metadata for further parsing
    """

    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        """Parse Union types, particularly Optional types.

        Arguments:
            input_type: The type to parse.
            metadata: Optional metadata associated with the type (will be preserved and passed through).

        Returns:
            A Narwhals DType by extracting the non-None type and delegating to the chain.
        """
        # Handle Union types from typing module (including Optional)
        if isinstance(input_type, (_GenericAlias, GenericAlias)):
            origin = get_origin(input_type)
            if origin is Union:
                args = get_args(input_type)
                extracted_type, extracted_metadata = self._parse_union(args, metadata)

                # Recursively parse the extracted type with combined metadata
                return self.parser_chain.parse(extracted_type, extracted_metadata, strict=True)

        # Handle UnionType (PEP 604: T | U syntax)
        elif isinstance(input_type, UnionType):
            args = get_args(input_type)
            extracted_type, extracted_metadata = self._parse_union(args, metadata)

            # Recursively parse the extracted type with combined metadata
            return self.parser_chain.parse(extracted_type, extracted_metadata, strict=True)

        return None

    def _parse_union(
        self, union: tuple[type[Any], ...], outer_metadata: tuple = ()
    ) -> tuple[type[Any], tuple[Any, ...]]:
        """Extract the non-None type from a Union.

        Arguments:
            union: Tuple of types in the Union.
            outer_metadata: Metadata from the outer type (e.g., from Annotated[Optional[T], ...]).

        Returns:
            A tuple of (non-None type, preserved metadata tuple).
            The outer metadata is preserved to ensure constraints aren't lost.

        Raises:
            UnsupportedDTypeError: If the Union has more than 2 types or both types are not None.
        """
        if len(union) != 2:  # noqa: PLR2004
            msg = "Union with more than two types is not supported."
            raise UnsupportedDTypeError(msg)

        field0, field1 = union

        if field0 is not NoneType and field1 is not NoneType:
            msg = "Union with both types being not None is not supported."
            raise UnsupportedDTypeError(msg)

        # Extract the non-None type
        # Return the type as-is and preserve the outer metadata
        extracted_type = field1 if field0 is NoneType else field0

        # Preserve outer metadata (e.g., from Annotated[Optional[int], Gt(0)])
        return (extracted_type, outer_metadata)


__all__ = ("UnionTypeParser",)
