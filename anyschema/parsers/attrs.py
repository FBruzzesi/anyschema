from __future__ import annotations

from typing import TYPE_CHECKING, Any

import narwhals as nw

from anyschema._dependencies import is_attrs_class
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import AttrsClassType


__all__ = ("AttrsTypeStep",)


class AttrsTypeStep(ParserStep):
    """Parser for attrs-specific types.

    Handles:

    - attrs classes (Struct types)

    Warning:
        It requires [attrs](https://www.attrs.org/) to be installed.
    """

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:  # noqa: ARG002
        """Parse attrs-specific types into Narwhals dtypes.

        Arguments:
            input_type: The type to parse.
            metadata: Optional metadata associated with the type.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        if is_attrs_class(input_type):
            return self._parse_attrs_class(input_type)

        # This parser doesn't handle this type
        return None

    def _parse_attrs_class(self, attrs_class: AttrsClassType) -> DType:
        """Parse an attrs class into a Struct type.

        Arguments:
            attrs_class: The attrs class.

        Returns:
            A Narwhals Struct dtype.
        """
        from anyschema.adapters import attrs_adapter

        return nw.Struct(
            [
                nw.Field(name=field_name, dtype=self.pipeline.parse(field_type, field_metadata, strict=True))
                for field_name, field_type, field_metadata in attrs_adapter(attrs_class)
            ]
        )
