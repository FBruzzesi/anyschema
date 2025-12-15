from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from typing_extensions import get_args, get_origin  # noqa: UP035

from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


class AnnotatedStep(ParserStep):
    """Parser for `typing.Annotated` types.

    Handles:

    - `Annotated[T, metadata...]` - extracts the type and metadata for further parsing
    """

    def parse(self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata) -> DType | None:
        """Parse Annotated types by extracting the base type and constraints.

        Arguments:
            input_type: The type to parse.
            constraints: Constraints associated with the type.
            metadata: Custom metadata dictionary.

        Returns:
            A Narwhals DType by extracting the base type and delegating to the chain.
        """
        if get_origin(input_type) is Annotated and (args := get_args(input_type)) is not None:
            base_type, *extra_constraints = args
            return self.pipeline.parse(base_type, (*constraints, *extra_constraints), metadata, strict=True)

        return None
