from __future__ import annotations

from types import NoneType
from typing import TYPE_CHECKING, Annotated, ForwardRef, NamedTuple, Union

from typing_extensions import get_args, get_origin  # noqa: UP035

from anyschema._metadata import partition_markers
from anyschema._utils import is_union_type
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from collections.abc import Callable

    from narwhals.dtypes import DType

    from anyschema._metadata import WithAnySchema
    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


class FieldTypeParts(NamedTuple):
    """A field type split by `split_field_markers`."""

    field_type: FieldType
    """The type without its field-level markers."""
    markers: tuple[WithAnySchema, ...]
    """The field-level markers, innermost first."""
    contains_none: bool
    """Whether the field-level type contains `None`, e.g. `T | None` but not `list[T | None]`."""


def split_field_markers(
    input_type: FieldType,
    resolve_forward_ref: Callable[[ForwardRef], FieldType] | None = None,
    *,
    inside_optional: bool = False,
) -> FieldTypeParts:
    """Split the field-level `Annotated` markers off a field type.

    Field-level markers sit in the `Annotated` layers of the type, optionally wrapped in a single `| None`. Deeper
    markers (e.g. inside `list[...]`) stay in place for `AnnotatedStep`.

    Arguments:
        input_type: The field type.
        resolve_forward_ref: Resolves forward references in the field-level layers, so that their markers and `| None`
            are field level too. A reference it cannot resolve is kept as is.
        inside_optional: Whether a field-level `| None` is already unwrapped. Only set when recursing.

    Returns:
        The field type split into its parts. The type is returned unchanged when it has no field-level markers.

    Examples:
        >>> from typing import Annotated, Optional
        >>> from anyschema import WithAnySchema
        >>> marker = WithAnySchema(unique=True)
        >>> parts = split_field_markers(Annotated[int, marker] | None)
        >>> parts.field_type == Optional[int], parts.markers, parts.contains_none
        (True, (WithAnySchema(unique=True),), True)
    """
    if isinstance(input_type, ForwardRef) and resolve_forward_ref is not None:
        try:
            resolved_type = resolve_forward_ref(input_type)
        except NotImplementedError:
            # Parsing it raises later, unless a `dtype` override skips parsing.
            return FieldTypeParts(input_type, (), inside_optional)
        return split_field_markers(resolved_type, resolve_forward_ref, inside_optional=inside_optional)

    if get_origin(input_type) is Annotated:
        base_type, *extras = get_args(input_type)
        inner = split_field_markers(base_type, resolve_forward_ref, inside_optional=inside_optional)
        markers, other_extras = partition_markers(extras)
        if not (markers or inner.markers):
            return FieldTypeParts(input_type, (), inner.contains_none)
        field_type = Annotated[(inner.field_type, *other_extras)] if other_extras else inner.field_type  # pyrefly: ignore[not-a-type]
        return FieldTypeParts(field_type, (*inner.markers, *markers), inner.contains_none)

    # Only the first `| None` layer is field level: stop at a second one.
    if not inside_optional and is_union_type(input_type) and NoneType in (args := get_args(input_type)):
        non_none_args = [arg for arg in args if arg is not NoneType]
        if len(non_none_args) > 1:  # e.g. `int | str | None`: nullable, with no markers to unwrap
            return FieldTypeParts(input_type, (), contains_none=True)
        inner = split_field_markers(non_none_args[0], resolve_forward_ref, inside_optional=True)
        # `Union[...]` rather than `|`, which fails on ForwardRef
        field_type = Union[(inner.field_type, None)] if inner.markers else input_type  # noqa: UP007  # pyrefly: ignore[not-a-type]
        return FieldTypeParts(field_type, inner.markers, contains_none=True)

    return FieldTypeParts(input_type, (), inside_optional)


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
