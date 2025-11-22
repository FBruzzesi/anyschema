from __future__ import annotations

from types import GenericAlias
from typing import TYPE_CHECKING, Annotated, _GenericAlias, get_args, get_origin  # type: ignore[attr-defined]

from anyschema.parsers._base import TypeParser

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
        if isinstance(input_type, (_GenericAlias, GenericAlias)):
            origin = get_origin(input_type)
            if origin is Annotated:
                args = get_args(input_type)
                if args:
                    base_type = args[0]
                    extra_metadata = args[1:] if len(args) > 1 else ()
                    return self.parser_chain.parse(base_type, (*metadata, *extra_metadata), strict=True)

        return None
