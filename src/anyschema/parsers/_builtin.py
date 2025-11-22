from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from inspect import isclass
from types import GenericAlias
from typing import TYPE_CHECKING, _GenericAlias, get_args, get_origin  # type: ignore[attr-defined]

import narwhals as nw

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import TypeParser

if TYPE_CHECKING:
    from narwhals.dtypes import DType


class PyTypeParser(TypeParser):
    """Parser for standard Python types."""

    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:  # noqa: C901, PLR0911, PLR0912
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

        # Handle generic type: list[T], tuple[T, ...], Sequence[T], Iterable[T]
        if isinstance(input_type, (_GenericAlias, GenericAlias)):
            return self._parse_generic(input_type, metadata)

        # This parser doesn't handle this type
        return None

    def _parse_generic(self, input_type: _GenericAlias | GenericAlias, metadata: tuple) -> DType | None:  # type: ignore[no-any-unimported]
        """Parse generic types like list[int].

        Arguments:
            input_type: The generic type to parse.
            metadata: Optional metadata associated with the type.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        origin, args = get_origin(input_type), get_args(input_type)
        if (not args) and (origin in (list, tuple, Sequence, Iterable)):
            return nw.List(nw.Object())

        inner_dtype = self.parser_chain.parse(args[0], metadata=metadata, strict=True)
        if inner_dtype is None:
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
