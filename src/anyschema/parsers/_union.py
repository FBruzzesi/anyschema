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
    """Parser for `T | None`, `Optional[T]` and `Union[T, None]`: parses `T`.

    It does not set field nullability, since it also runs on nested types such as the `T | None` in `list[T | None]`.
    [`ParserPipeline.parse_into_field`][anyschema.parsers.ParserPipeline.parse_into_field] sets it from the field-level
    type.
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
        if get_origin(input_type) is Union or isinstance(input_type, UnionType):
            args = get_args(input_type)
            extracted_type = self._parse_union(args)
            return self.pipeline.parse(extracted_type, constraints, metadata, strict=True)
        return None

    def _parse_union(self, union: tuple[FieldType, ...]) -> FieldType:
        if len(union) != 2:  # noqa: PLR2004
            msg = "Union with more than two types is not supported."
            raise UnsupportedDTypeError(msg)

        field0, field1 = union
        if field0 is not NoneType and field1 is not NoneType:
            msg = "Union with mixed types is not supported."
            raise UnsupportedDTypeError(msg)

        return field1 if field0 is NoneType else field0
