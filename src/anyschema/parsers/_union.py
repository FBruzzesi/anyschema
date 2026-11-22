from __future__ import annotations

from types import NoneType
from typing import TYPE_CHECKING

from typing_extensions import get_args  # noqa: UP035

from anyschema._utils import is_union_type
from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


class UnionTypeStep(ParserStep):
    """Parser for `T | None`, `Optional[T]` and `Union[T, None]`: it parses `T`.

    It does not set `nullable`, because it also parses nested types such as the elements of `list[T | None]`.
    [`ParserPipeline.parse_into_field`][anyschema.parsers.ParserPipeline.parse_into_field] decides nullability.
    """

    def parse(self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata) -> DType | None:
        """Parse the non-None member of a `T | None` union.

        Arguments:
            input_type: The type to parse.
            constraints: Constraints associated with the type, passed through.
            metadata: Custom metadata dictionary, passed through.

        Returns:
            The dtype of `T`, or `None` if `input_type` is not a union.

        Raises:
            UnsupportedDTypeError: If the union is not `T | None`.
        """
        if not is_union_type(input_type):
            return None

        args = get_args(input_type)
        if len(args) != 2:  # noqa: PLR2004
            msg = "Union with more than two types is not supported."
            raise UnsupportedDTypeError(msg)
        if NoneType not in args:
            msg = "Union with mixed types is not supported."
            raise UnsupportedDTypeError(msg)

        inner_type = args[1] if args[0] is NoneType else args[0]
        return self.pipeline.parse(inner_type, constraints, metadata, strict=True)
