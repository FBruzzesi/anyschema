from __future__ import annotations

from types import NoneType, UnionType
from typing import TYPE_CHECKING, Annotated, Union

from typing_extensions import get_args, get_origin  # noqa: UP035

from anyschema._metadata import partition_markers
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema._metadata import WithAnySchema
    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


def split_field_markers(input_type: FieldType) -> tuple[FieldType, tuple[WithAnySchema, ...], bool]:
    """Split the field-level `Annotated` markers off a field type.

    Field-level markers sit in the `Annotated` layers of the type, optionally wrapped in a single `T | None`. Deeper
    markers (e.g. inside `list[...]`) stay in place for `AnnotatedStep`.

    Returns:
        A tuple of `(type without field-level markers, markers innermost first, whether the type is optional)`. The
        input type is returned unchanged when it has no field-level markers.

    Examples:
        >>> from typing import Annotated, Optional
        >>> from anyschema import WithAnySchema
        >>> marker = WithAnySchema(unique=True)
        >>> input_type, markers, is_optional = split_field_markers(Annotated[int, marker] | None)
        >>> input_type == Optional[int], markers, is_optional
        (True, (WithAnySchema(unique=True),), True)
    """
    return _split_field_markers(input_type, inside_optional=False)


def _split_field_markers(
    input_type: FieldType, *, inside_optional: bool
) -> tuple[FieldType, tuple[WithAnySchema, ...], bool]:
    if get_origin(input_type) is Annotated:
        base_type, *extras = get_args(input_type)
        inner_type, inner_markers, is_optional = _split_field_markers(base_type, inside_optional=inside_optional)
        markers, other_extras = partition_markers(extras)
        if not (markers or inner_markers):
            return input_type, (), is_optional
        stripped_type = Annotated[(inner_type, *other_extras)] if other_extras else inner_type  # pyrefly: ignore[not-a-type]
        return stripped_type, (*inner_markers, *markers), is_optional

    args = get_args(input_type)
    is_union = get_origin(input_type) is Union or isinstance(input_type, UnionType)
    # Only the first `| None` layer is field level: stop at a second one.
    if not inside_optional and is_union and len(args) == 2 and NoneType in args:  # noqa: PLR2004
        (non_none_type,) = (arg for arg in args if arg is not NoneType)
        inner_type, markers, _ = _split_field_markers(non_none_type, inside_optional=True)
        # `Union[...]` rather than `|`, which fails on ForwardRef
        stripped_type = Union[(inner_type, None)] if markers else input_type  # noqa: UP007  # pyrefly: ignore[not-a-type]
        return stripped_type, markers, True

    return input_type, (), inside_optional


class AnnotatedStep(ParserStep):
    """Parser for `typing.Annotated` types.

    Handles:

    - `Annotated[T, metadata...]` - extracts the type and metadata for further parsing
    - Nested [`WithAnySchema`][anyschema.WithAnySchema] markers: the last `dtype` wins and `T` is not parsed. A nested
        marker setting any other key raises.

    [`ParserPipeline.parse_into_field`][anyschema.parsers.ParserPipeline.parse_into_field] removes field-level markers
    before parsing.
    """

    def parse(self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata) -> DType | None:
        """Parse Annotated types by extracting the base type and constraints.

        Arguments:
            input_type: The type to parse.
            constraints: Constraints associated with the type.
            metadata: Custom metadata dictionary.

        Returns:
            A Narwhals DType by extracting the base type and delegating to the chain.

        Raises:
            NotImplementedError: If a marker sets anything other than `dtype`.
        """
        if get_origin(input_type) is not Annotated:
            return None

        base_type, *extras = get_args(input_type)
        markers, other_extras = partition_markers(extras)
        if any(marker.custom or marker.anyschema.keys() - {"dtype"} for marker in markers):
            msg = (
                "Nested `WithAnySchema` markers can only set `dtype`: other metadata is only supported at the field "
                "level, i.e. in the `Annotated` layers of a field type, optionally wrapped in a single `| None`. "
                f"Found it nested in {input_type!r}.\n\n"
                "Fields of nested structs (models, dataclasses, TypedDicts, ...) count as nested."
            )
            raise NotImplementedError(msg)
        if dtypes := [dtype for marker in markers if (dtype := marker.dtype) is not None]:
            return dtypes[-1]

        return self.pipeline.parse(base_type, (*constraints, *other_extras), metadata, strict=True)
