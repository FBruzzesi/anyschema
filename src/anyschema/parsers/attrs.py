from __future__ import annotations

from typing import TYPE_CHECKING

from anyschema._dependencies import is_attrs_class
from anyschema.adapters import attrs_adapter
from anyschema.parsers._base import ParserStep, parse_struct

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


__all__ = ("AttrsTypeStep",)


class AttrsTypeStep(ParserStep):
    """Parser for attrs-specific types.

    Handles:

    - attrs classes (Struct types)

    Warning:
        It requires [attrs](https://www.attrs.org/) to be installed.
    """

    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,  # noqa: ARG002
        metadata: FieldMetadata,  # noqa: ARG002
    ) -> DType | None:
        """Parse attrs-specific types into Narwhals dtypes.

        Arguments:
            input_type: The type to parse.
            constraints: Constraints associated with the type.
            metadata: Custom metadata dictionary.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        if is_attrs_class(input_type):
            return parse_struct(self.pipeline, attrs_adapter(input_type))

        # This parser doesn't handle this type
        return None
