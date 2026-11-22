from __future__ import annotations

from types import NoneType
from typing import TYPE_CHECKING, Annotated, ForwardRef, Literal, Union

from typing_extensions import get_args, get_origin  # noqa: UP035

from anyschema._metadata import partition_markers
from anyschema._utils import is_union_type
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from collections.abc import Callable

    from narwhals.dtypes import DType

    from anyschema._metadata import WithAnySchema
    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


def split_field_markers(
    input_type: FieldType,
    resolve_forward_ref: Callable[[ForwardRef], FieldType] | None = None,
    *,
    inside_optional: bool = False,
) -> tuple[FieldType, tuple[WithAnySchema, ...]]:
    """Split the field-level `WithAnySchema` markers off a field type.

    The field level is the `Annotated` layers of the type, optionally wrapped in a single `T | None`. Deeper markers
    (e.g. inside `list[...]`) stay in place for `AnnotatedStep`. Field-level forward references are resolved with
    `resolve_forward_ref`; one that fails to resolve is kept as is.

    Arguments:
        input_type: The field type.
        resolve_forward_ref: Resolves forward references. `None` leaves them unresolved.
        inside_optional: Whether a `| None` layer was already crossed. A second one is not field level.

    Returns:
        The type without field-level markers, which keeps its `| None`, and the markers, innermost first. The input
        type itself when there is nothing to strip or resolve.

    Examples:
        >>> from typing import Annotated, Optional
        >>> from anyschema import WithAnySchema
        >>> marker = WithAnySchema(unique=True)
        >>> input_type, markers = split_field_markers(Annotated[int, marker] | None)
        >>> input_type == Optional[int], markers
        (True, (WithAnySchema(unique=True),))
    """
    if isinstance(input_type, ForwardRef) and resolve_forward_ref is not None:
        try:
            resolved_type = resolve_forward_ref(input_type)
        except (NotImplementedError, SyntaxError):  # `SyntaxError`: a malformed ref, raised here on Python 3.14+
            return input_type, ()  # shortcut: hides the `None` of an unresolvable ref, set `nullable` explicitly then
        return split_field_markers(resolved_type, resolve_forward_ref, inside_optional=inside_optional)

    if get_origin(input_type) is Annotated:
        base_type, *extras = get_args(input_type)
        inner_type, inner_markers = split_field_markers(base_type, resolve_forward_ref, inside_optional=inside_optional)
        markers, other_extras = partition_markers(extras)
        if not markers and inner_type is base_type:
            return input_type, ()
        stripped_type = Annotated[(inner_type, *other_extras)] if other_extras else inner_type  # pyrefly: ignore[not-a-type]
        return stripped_type, (*inner_markers, *markers)

    args = get_args(input_type)
    if not inside_optional and is_union_type(input_type) and len(args) == 2 and NoneType in args:  # noqa: PLR2004
        (non_none_type,) = (arg for arg in args if arg is not NoneType)
        inner_type, markers = split_field_markers(non_none_type, resolve_forward_ref, inside_optional=True)
        if inner_type is non_none_type:
            return input_type, ()
        # `Union[...]` because `|` fails on a `ForwardRef`
        return Union[(inner_type, None)], markers  # noqa: UP007  # pyrefly: ignore[not-a-type]

    return input_type, ()


def field_contains_none(input_type: FieldType) -> bool:
    """Whether the field-level type contains `None`.

    The field level is the `Annotated` layers and the first union or `Literal` they wrap: `T | None` and
    `Literal[..., None]` count, the elements of `list[T | None]` do not. A forward reference counts as not containing
    `None`: resolve it first with [`split_field_markers`][anyschema.parsers._annotated.split_field_markers].

    Examples:
        >>> from typing import Annotated, Literal, Optional
        >>> field_contains_none(Annotated[int, "meta"] | None), field_contains_none(Literal["a", None])
        (True, True)
        >>> field_contains_none(list[Optional[int]])
        False
    """
    if get_origin(input_type) is Annotated:
        return field_contains_none(get_args(input_type)[0])
    if is_union_type(input_type):
        return NoneType in get_args(input_type)
    return get_origin(input_type) is Literal and None in get_args(input_type)


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
