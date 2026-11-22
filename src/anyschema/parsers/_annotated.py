from __future__ import annotations

from types import NoneType
from typing import TYPE_CHECKING, Annotated, ForwardRef, Literal

from typing_extensions import get_args, get_origin  # noqa: UP035

from anyschema._utils import is_union_type
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from collections.abc import Callable

    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


def field_contains_none(
    input_type: FieldType, resolve_forward_ref: Callable[[ForwardRef], FieldType] | None = None
) -> bool:
    """Whether the field-level type contains `None`.

    The field level is the `Annotated` layers and the first union or `Literal` they wrap: `T | None` and
    `Literal[..., None]` count, the elements of `list[T | None]` do not.

    Arguments:
        input_type: The field type.
        resolve_forward_ref: Resolves forward references at the field level. An unresolvable one counts as not
            containing `None`.

    Examples:
        >>> from typing import Annotated, Literal, Optional
        >>> field_contains_none(Annotated[int, "meta"] | None), field_contains_none(Literal["a", None])
        (True, True)
        >>> field_contains_none(list[Optional[int]])
        False
    """
    if get_origin(input_type) is Annotated:
        return field_contains_none(get_args(input_type)[0], resolve_forward_ref)
    if isinstance(input_type, ForwardRef) and resolve_forward_ref is not None:
        try:
            resolved_type = resolve_forward_ref(input_type)
        except (NotImplementedError, SyntaxError):  # `SyntaxError`: a malformed ref, raised here on Python 3.14+
            return False  # shortcut: hides the `None` of an unresolvable ref, set `nullable` explicitly then
        return field_contains_none(resolved_type, resolve_forward_ref)
    if is_union_type(input_type):
        return NoneType in get_args(input_type)
    return get_origin(input_type) is Literal and None in get_args(input_type)


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
        if get_origin(input_type) is Annotated:
            base_type, *extra_constraints = get_args(input_type)
            return self.pipeline.parse(base_type, (*constraints, *extra_constraints), metadata, strict=True)

        return None
