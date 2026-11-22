from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum, Flag
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

import narwhals as nw
from typing_extensions import get_args, get_origin  # noqa: UP035

from anyschema._dependencies import is_dataclass, is_typed_dict
from anyschema._metadata import get_anyschema_value_by_key
from anyschema._utils import int_dtype_from_bounds
from anyschema.adapters import dataclass_adapter, typed_dict_adapter
from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep, parse_struct

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.parsers._pipeline import ParserPipeline
    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType

# `IPv4Interface`/`IPv6Interface` subclass the `Address` types
_STDLIB_STRING_TYPES = (str, UUID, PurePath, IPv4Address, IPv6Address, IPv4Network, IPv6Network)


class PyTypeStep(ParserStep):
    """Parser for Python builtin types.

    Handles:

    - `int`, `float`, `decimal`, `str`, `bytes`, `bool`, `date`, `datetime`, `timedelta`, `time`, `object`
    - `Enum` and `Literal`: string values give an `Enum` dtype, int values the smallest int dtype that fits them
        (`Literal[1, 2]` gives `UInt8`), other values the dtype of their type. `Flag` enums give `Int64`.
    - `UUID`, `pathlib` paths and `ipaddress` types, as String
    - generics: `list[T]`, `Sequence[T]`, `Iterable[T]`, `tuple[T, ...]`
    - `dict`, `Mapping[K, V]`, typed dictionaries (`TypedDict`) and dataclasses
    """

    def parse(self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata) -> DType | None:  # noqa: C901, PLR0912
        """Parse Python type annotations into Narwhals dtypes.

        Arguments:
            input_type: The type to parse.
            constraints: Constraints associated with the type.
            metadata: Custom metadata dictionary.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        # Handle generic types first: list[T], tuple[T, ...], Sequence[T], Iterable[T], dict[K, V], Literal[...]
        # Note: In Python 3.10, generic aliases like list[int] pass isinstance(input_type, type),
        # but they cannot be used with issubclass() against abstract base classes like Sequence/Iterable.
        # Checking get_origin() first avoids this issue.
        if (origin := get_origin(input_type)) is not None:
            return self._parse_generic(input_type, origin, constraints, metadata)

        # Now handle actual classes (not generic aliases)
        if isinstance(input_type, type):
            # NOTE: The order is quite important. In fact:
            #   * issubclass(MyEnum(str, Enum), str) -> True
            #   * issubclass(bool, int) -> True
            #   * issubclass(TypedDict, dict) -> True
            #   * issubclass(datetime, date) -> True
            if issubclass(input_type, Flag):  # Members combine (`READ | WRITE`), so the values are unbounded.
                return nw.Int64()
            if issubclass(input_type, Enum):
                return parse_enum_values(
                    self.pipeline, [member.value for member in input_type], input_type, constraints, metadata
                )
            if issubclass(input_type, _STDLIB_STRING_TYPES):
                return nw.String()
            if issubclass(input_type, bool):
                return nw.Boolean()
            if issubclass(input_type, int):
                return nw.Int64()
            if issubclass(input_type, float):
                return nw.Float64()
            if issubclass(input_type, datetime):
                return nw.Datetime(
                    time_unit=get_anyschema_value_by_key(metadata, key="time_unit", default="us"),
                    time_zone=get_anyschema_value_by_key(metadata, key="time_zone"),
                )
            if issubclass(input_type, date):
                return nw.Date()
            if issubclass(input_type, timedelta):
                return nw.Duration()
            if issubclass(input_type, time):
                return nw.Time()
            if issubclass(input_type, Decimal):
                return nw.Decimal(
                    precision=get_anyschema_value_by_key(metadata, key="precision"),
                    scale=get_anyschema_value_by_key(metadata, key="scale") or 0,
                )
            if issubclass(input_type, bytes):
                return nw.Binary()
            if is_typed_dict(input_type):
                return parse_struct(self.pipeline, typed_dict_adapter(input_type))
            if is_dataclass(input_type):
                return parse_struct(self.pipeline, dataclass_adapter(input_type))
            if issubclass(input_type, dict):  # Plain dict without type parameters -> Struct with Object fields
                return nw.Struct([])
            # TODO(FBruzzesi): https://github.com/FBruzzesi/anyschema/issues/56
            if issubclass(input_type, (set, frozenset)):
                return None
            if issubclass(input_type, (list, tuple, Sequence, Iterable)):
                return nw.List(nw.Object())

        if input_type is object:
            return nw.Object()

        return None

    def _parse_generic(
        self, input_type: FieldType, origin: Any, constraints: FieldConstraints, metadata: FieldMetadata
    ) -> DType | None:
        """Parse generic types like `list[int]`, `dict[str, int]` and `Literal[...]`.

        Arguments:
            input_type: The generic type to parse.
            origin: result of `get_origin(input_type)`, passed to avoid recomputing it.
            constraints: Constraints associated with the type.
            metadata: Custom metadata dictionary.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        if origin is Literal:
            # `parse_into_field` makes a field-level `Literal[..., None]` nullable.
            values = [value for value in get_args(input_type) if value is not None]
            return parse_enum_values(self.pipeline, values, input_type, constraints, metadata)

        if origin in {dict, Mapping}:
            # For now, we treat dict[K, V] as an empty Struct
            # TODO(FBruzzesi): What's a better way to map this? We should introspect the mapping values
            return nw.Struct([])

        if origin not in {list, Sequence, Iterable, tuple}:
            return None

        if not (args := get_args(input_type)):  # Bare `typing.List`, `typing.Sequence`, ...
            return nw.List(nw.Object())

        inner_dtype = self.pipeline.parse(args[0], constraints=constraints, metadata=metadata, strict=True)

        if origin is tuple and args[-1] is not Ellipsis:  # Fixed length: `tuple[T, T]`
            if len(set(args)) != 1:
                msg = f"Tuple with mixed types is not supported: {input_type}"
                raise UnsupportedDTypeError(msg)
            return nw.Array(inner_dtype, shape=len(args))

        return nw.List(inner_dtype)


def parse_enum_values(
    pipeline: ParserPipeline,
    values: Sequence[Any],
    source: FieldType,
    constraints: FieldConstraints,
    metadata: FieldMetadata,
) -> DType:
    """Parse the values of an `Enum`, a `Literal` or a JSON Schema `enum`/`const`.

    Strings give an `Enum` dtype (Narwhals `Enum` categories must be strings), ints the smallest int dtype that
    fits them, and any other type its own dtype. `None` is not special here: callers drop it first.

    Arguments:
        pipeline: The pipeline that parses the type of non-string, non-int values.
        values: The values.
        source: The type or schema the values come from, for the error message.
        constraints: Constraints passed on to the pipeline.
        metadata: Metadata passed on to the pipeline.

    Returns:
        The Narwhals dtype of the values.

    Raises:
        UnsupportedDTypeError: If there are no values, or they have more than one type.
    """
    value_types = {type(value) for value in values}
    if len(value_types) != 1:
        msg = (
            f"Cannot infer a dtype for {source}: its values must be non-empty and of a single type. "
            "Set the dtype explicitly with `{'anyschema': {'dtype': ...}}` metadata."
        )
        raise UnsupportedDTypeError(msg)
    value_type = value_types.pop()
    if value_type is str:
        return nw.Enum(values)
    if value_type is int:
        return int_dtype_from_bounds(min(values), max(values))
    return pipeline.parse(value_type, constraints=constraints, metadata=metadata)
