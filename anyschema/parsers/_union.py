from __future__ import annotations

from types import NoneType, UnionType
from typing import TYPE_CHECKING, Union

from typing_extensions import get_args, get_origin  # noqa: UP035

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


class UnionTypeStep(ParserStep):
    """Parser for Union types including `Optional`.

    Handles:

    - `Union[T, None]`, `T | None`, `Optional[T]`
    - Extracts the non-None type and its metadata for further parsing
    """

    def parse(self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata) -> DType | None:
        """Parse Union types, particularly Optional types.

        Arguments:
            input_type: The type to parse.
            constraints: Constraints associated with the type (will be preserved and passed through).
            metadata: Custom metadata dictionary (will be preserved and passed through).

        Returns:
            A Narwhals DType by extracting the non-None type and delegating to the chain.
        """
        # Handle Union types from typing module (including Optional)
        # Handle UnionType (PEP 604: T | U syntax)
        if get_origin(input_type) is Union or isinstance(input_type, UnionType):
            args = get_args(input_type)
            extracted_type = self._parse_union(args)

            # Set nullable metadata if not already explicitly set
            # This way Union[T, None] / Optional[T] automatically marks the field as nullable
            # We mutate the metadata dict in-place so parse_field can read it
            if "anyschema/nullable" not in metadata:
                metadata["anyschema/nullable"] = True
            return self.pipeline.parse(extracted_type, constraints, metadata, strict=True)

        return None

    def _parse_union(self, union: tuple[FieldType, ...]) -> FieldType:
        """Extract the non-None type from a Union.

        Arguments:
            union: Tuple of types in the Union.
            outer_constraints: Constraints from the outer type (e.g., from Annotated[Optional[T], ...]).

        Returns:
            A tuple of (non-None type, preserved constraints tuple).
            The outer constraints are preserved to ensure constraints aren't lost.

        Raises:
            UnsupportedDTypeError: If the Union has more than 2 types or both types are not None.
        """
        if len(union) != 2:  # noqa: PLR2004
            msg = "Union with more than two types is not supported."
            raise UnsupportedDTypeError(msg)

        field0, field1 = union

        if field0 is not NoneType and field1 is not NoneType:
            msg = "Union with mixed types is not supported."
            raise UnsupportedDTypeError(msg)

        return field1 if field0 is NoneType else field0
