from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

import narwhals as nw
from typing_extensions import get_args, get_origin, get_type_hints  # noqa: UP035

from anyschema._dependencies import is_typed_dict
from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import TypedDictType


class PyTypeStep(ParserStep):
    """Parser for Python builtin types.

    Handles:

    - `int`, `float`, `decimal`, `str`, `bytes`, `bool`, `date`, `datetime`, `timedelta`, `time`, `object`, `Enum`,
        `Literal`
    - generics: `list[T]`, `Sequence[T]`, `Iterable[T]`, `tuple[T, ...]`
    - `dict`,` Mapping[K, V]`, and typed dictionaries (`TypedDict`)
    """

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:  # noqa: C901, PLR0911, PLR0912
        """Parse Python type annotations into Narwhals dtypes.

        Arguments:
            input_type: The type to parse.
            metadata: Optional metadata associated with the type.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        if isinstance(input_type, type):
            # NOTE: The order is quite important. In fact:
            #   * issubclass(MyEnum(str, Enum), str) -> True
            #   * issubclass(bool, int) -> True
            #   * issubclass(TypedDict, dict) -> True
            #   * issubclass(datetime, date) -> True
            if issubclass(input_type, Enum):
                return nw.Enum(input_type)
            if issubclass(input_type, str):
                return nw.String()
            if issubclass(input_type, bool):
                return nw.Boolean()
            if issubclass(input_type, int):
                return nw.Int64()
            if issubclass(input_type, float):
                return nw.Float64()
            if issubclass(input_type, datetime):
                return nw.Datetime("us")
            if issubclass(input_type, date):
                return nw.Date()
            if issubclass(input_type, timedelta):
                return nw.Duration()
            if issubclass(input_type, time):
                return nw.Time()
            if issubclass(input_type, Decimal):
                return nw.Decimal()
            if issubclass(input_type, bytes):
                return nw.Binary()
            if is_typed_dict(input_type):
                return self._parse_typed_dict(input_type, metadata)
            if issubclass(input_type, dict):  # Plain dict without type parameters -> Struct with Object fields
                return nw.Struct([])
            if issubclass(input_type, (set, frozenset)):  # TODO(FBruzzesi): Decide if we should map these to List
                return None
            if issubclass(input_type, (list, tuple, Sequence, Iterable)):
                return nw.List(nw.Object())

        # Handle generic types: list[T], tuple[T, ...], Sequence[T], Iterable[T], dict[K, V], Literal[...]
        if (origin := get_origin(input_type)) is not None:
            return self._parse_generic(input_type, origin, metadata)

        if input_type is object:
            return nw.Object()

        return None

    def _parse_generic(self, input_type: Any, origin: Any, metadata: tuple) -> DType | None:  # noqa: PLR0911
        """Parse generic types like list[int], dict[str, int].

        Arguments:
            input_type: The generic type to parse.
            origin: result of `get_origin(input_type)`, passed to avoid recomputing it.
            metadata: Optional metadata associated with the type.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        if origin is Literal:
            return nw.Enum(get_args(input_type))

        if origin in (dict, Mapping):
            # For now, we treat dict[K, V] as an empty Struct
            # TODO(FBruzzesi): What's a better way to map this? We should introspect the mapping values
            return nw.Struct([])

        args = get_args(input_type)
        inner_dtype = self.pipeline.parse(args[0], metadata=metadata, strict=True)

        if inner_dtype is None:  # pragma: no cover
            return None

        if origin in (list, Sequence, Iterable):
            return nw.List(inner_dtype)

        if origin is tuple:
            if len(args) == 2 and args[1] is Ellipsis:  # noqa: PLR2004
                # tuple[T, ...] - variable length tuple
                return nw.List(inner_dtype)

            if len(set(args)) != 1:
                msg = f"Tuple with mixed types is not supported: {input_type}"
                raise UnsupportedDTypeError(msg)

            return nw.Array(inner_dtype, shape=len(args))

        return None

    def _parse_typed_dict(self, typed_dict: TypedDictType, metadata: tuple) -> DType:  # noqa: ARG002
        """Parse a TypedDict into a Struct type.

        Arguments:
            typed_dict: The TypedDict class.
            metadata: Optional metadata associated with the type.

        Returns:
            A Narwhals Struct dtype.
        """
        try:
            type_hints = get_type_hints(typed_dict)
        except Exception:  # pragma: no cover  # noqa: BLE001
            # If we can't get type hints, use __annotations__
            type_hints = getattr(typed_dict, "__annotations__", {})

        fields = [
            nw.Field(name=field_name, dtype=self.pipeline.parse(field_type, metadata=()))
            for field_name, field_type in type_hints.items()
        ]
        return nw.Struct(fields)
