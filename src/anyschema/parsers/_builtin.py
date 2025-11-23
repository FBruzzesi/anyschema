from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from inspect import isclass
from types import GenericAlias
from typing import TYPE_CHECKING, Any, _GenericAlias, get_args, get_origin, get_type_hints  # type: ignore[attr-defined]

import narwhals as nw

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType


class PyTypeStep(ParserStep):
    """Parser for Python builtin types.

    Handles:
    - int, float, decimal, str, bytes, bool, date, datetime, timedelta, time, object, enum
    - generics: list[T], Sequence[T], Iterable[T], tuple[T, ...]
    - dict, Mapping[K, V], and typed dictionaries (TypedDict)
    """

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:  # noqa: C901, PLR0911, PLR0912
        """Parse Python type annotations into Narwhals dtypes.

        Arguments:
            input_type: The type to parse.
            metadata: Optional metadata associated with the type.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        if input_type is int:
            return nw.Int64()
        if input_type is float:
            return nw.Float64()
        if input_type is str:
            return nw.String()
        if input_type is bool:
            return nw.Boolean()
        if isinstance(input_type, type) and issubclass(input_type, datetime):
            return nw.Datetime("us")
        if isinstance(input_type, type) and issubclass(input_type, date):
            return nw.Date()
        if input_type is timedelta:
            return nw.Duration()
        if input_type is time:
            return nw.Time()
        if input_type is Decimal:
            return nw.Decimal()
        if input_type is bytes:
            return nw.Binary()
        if input_type is object:
            return nw.Object()
        if isclass(input_type) and issubclass(input_type, Enum):
            return nw.Enum(input_type)

        # Handle dict types (including TypedDict)
        if input_type is dict:
            # Plain dict without type parameters -> Struct with Object fields
            return nw.Struct([])

        if self._is_typed_dict(input_type):
            return self._parse_typed_dict(input_type, metadata)

        # Handle generic type: list[T], tuple[T, ...], Sequence[T], Iterable[T], dict[K, V]
        if isinstance(input_type, (_GenericAlias, GenericAlias)):
            return self._parse_generic(input_type, metadata)

        if input_type in (list, tuple, Sequence, Iterable):
            return nw.List(nw.Object())

        return None

    def _parse_generic(self, input_type: _GenericAlias | GenericAlias, metadata: tuple) -> DType | None:  # type: ignore[no-any-unimported]
        """Parse generic types like list[int], dict[str, int].

        Arguments:
            input_type: The generic type to parse.
            metadata: Optional metadata associated with the type.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        origin, args = get_origin(input_type), get_args(input_type)

        if origin in (dict, Mapping):
            # For now, we treat dict[K, V] as an empty Struct
            # TODO(FBruzzesi): What's a better way to map this? We should introspect the mapping values
            return nw.Struct([])

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

    @staticmethod
    def _is_typed_dict(input_type: Any) -> bool:
        """Check if a type is a TypedDict.

        Arguments:
            input_type: The type to check.

        Returns:
            True if the type is a TypedDict, False otherwise.
        """
        try:
            # TypedDict classes have __annotations__ and __total__ attributes
            return (
                hasattr(input_type, "__annotations__")
                and hasattr(input_type, "__total__")
                and hasattr(input_type, "__required_keys__")
                and hasattr(input_type, "__optional_keys__")
            )
        except (AttributeError, TypeError):  # pragma: no cover
            return False

    def _parse_typed_dict(self, typed_dict: type, metadata: tuple) -> DType:  # noqa: ARG002
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
