from __future__ import annotations

import ast
import re
from itertools import takewhile
from typing import TYPE_CHECKING, cast

from narwhals.dtypes import (
    Array,
    Binary,
    Boolean,
    Categorical,
    Date,
    Datetime,
    Decimal,
    Duration,
    Enum,
    Field,
    Float32,
    Float64,
    Int8,
    Int16,
    Int32,
    Int64,
    Int128,
    List,
    Object,
    String,
    Struct,
    Time,
    UInt8,
    UInt16,
    UInt32,
    UInt64,
    UInt128,
    Unknown,
)

if TYPE_CHECKING:
    from narwhals.dtypes import DType
    from narwhals.typing import TimeUnit


NON_COMPLEX_MAPPING = {
    "Binary": Binary(),
    "Boolean": Boolean(),
    "Categorical": Categorical(),
    "Date": Date(),
    "Decimal": Decimal(),
    "Float32": Float32(),
    "Float64": Float64(),
    "Int8": Int8(),
    "Int16": Int16(),
    "Int32": Int32(),
    "Int64": Int64(),
    "Int128": Int128(),
    "Object": Object(),
    "String": String(),
    "Time": Time(),
    "UInt8": UInt8(),
    "UInt16": UInt16(),
    "UInt32": UInt32(),
    "UInt64": UInt64(),
    "UInt128": UInt128(),
}

RGX_ARRAY = re.compile(r"^Array\((.+),\s*shape=(\(.+?\))\)$")
RGX_DATETIME = re.compile(r"^Datetime\(time_unit='([^']+)'(?:,\s*time_zone=(?:'([^']+)'|None))?\)$")
RGX_DURATION = re.compile(r"^Duration\(time_unit='([^']+)'\)$")
RGX_ENUM = re.compile(r"^Enum\(categories=(\[.*?\])\)$")
RGX_LIST = re.compile(r"^List\((.+)\)$")
RGX_STRUCT = re.compile(r"^Struct\(\{(.*)\}\)$")
RGX_FIELD_NAME = re.compile(r",? ?'([^']+)':")


__all__ = (
    "deserialize_dtype",
    "serialiaze_dtype",
)


def serialiaze_dtype(dtype: DType) -> str:
    """Serialize a Narwhals dtype to its string representation.

    Converts a Narwhals dtype object into a string that can be stored or transmitted
    and later reconstructed using `deserialize_dtype`. The serialization is based on
    the dtype's string representation.

    Arguments:
        dtype: A Narwhals DType object to serialize

    Returns:
        String representation of the dtype (e.g., "Int64", "List(String)", "Struct({'a': Int64, 'b': String})")

    Examples:
        >>> serialiaze_dtype(Int64())
        'Int64'
        >>> serialiaze_dtype(List(String()))
        'List(String)'
        >>> serialiaze_dtype(Datetime(time_unit="ms", time_zone="UTC"))
        "Datetime(time_unit='ms', time_zone='UTC')"
        >>> serialiaze_dtype(Struct({"a": Int64(), "b": String()}))
        "Struct({'a': Int64, 'b': String})"
    """
    return str(dtype)


def deserialize_dtype(into_dtype: str) -> DType:
    """Deserialize a string representation of a Narwhals dtype back to the dtype object.

    Handles both simple and complex nested types using regex and recursion.

    Arguments:
        into_dtype: String representation of the dtype (e.g., "Int64", "List(String)",
            "Struct({'a': Int64, 'b': List(String)})")

    Returns:
        The corresponding Narwhals DType object

    Examples:
        >>> deserialize_dtype("Int64")
        Int64
        >>> deserialize_dtype("List(String)")
        List(String)
        >>> deserialize_dtype("Datetime(time_unit='ms', time_zone='UTC')")
        Datetime(time_unit='ms', time_zone='UTC')
    """
    if (dtype := NON_COMPLEX_MAPPING.get(into_dtype)) is not None:
        return dtype

    if datetime_match := RGX_DATETIME.match(into_dtype):
        time_unit = cast("TimeUnit", datetime_match.group(1))
        time_zone = datetime_match.group(2) if datetime_match.group(2) else None
        return Datetime(time_unit=time_unit, time_zone=time_zone)

    if duration_match := RGX_DURATION.match(into_dtype):
        time_unit = cast("TimeUnit", duration_match.group(1))
        return Duration(time_unit=time_unit)

    if enum_match := RGX_ENUM.match(into_dtype):
        categories = ast.literal_eval(enum_match.group(1))
        return Enum(categories=categories)

    if list_match := RGX_LIST.match(into_dtype):
        inner_type = deserialize_dtype(list_match.group(1))
        return List(inner_type)

    if array_match := RGX_ARRAY.match(into_dtype):
        inner_type = deserialize_dtype(array_match.group(1))
        shape = ast.literal_eval(array_match.group(2))
        return Array(inner_type, shape=shape)

    if struct_match := RGX_STRUCT.match(into_dtype):
        fields = _parse_struct_fields(struct_match.group(1))
        return Struct(fields)

    return Unknown()


def _extract_field_name(fields_str: str, start_pos: int) -> tuple[str, int]:
    """Extract a field name from the struct string and progress the position.

    Arguments:
        fields_str: The full struct fields string
        start_pos: Position to start extracting from

    Returns:
        Tuple of (field_name, new_position) after the field name

    Note:
        Assumes well-formed input from Narwhals dtype string representation.
        Field names are always quoted with single quotes.
        Expected formats:
            * "'fieldname': dtype"
            * ", 'fieldname': dtype"
    """
    if match := RGX_FIELD_NAME.match(fields_str, start_pos):
        field_name = match.group(1)
        new_pos = match.end()

        return field_name, new_pos

    msg = f"Failed to parse field name from: {fields_str[start_pos:]}"
    raise ValueError(msg)


def _extract_field_dtype(fields_str: str, start_pos: int) -> tuple[str, int]:
    """Extract a dtype value string, tracking depth for nested structures.

    Arguments:
        fields_str: The full struct fields string
        start_pos: Position to start extracting from

    Returns:
        Tuple of (dtype_string, new_position) after the dtype value

    Note:
        Assumes well-formed input from Narwhals dtype string representation.
    """
    depth = 0
    end_pos = start_pos

    for char in fields_str[start_pos:]:
        if char in "({[":
            depth += 1
        elif char in ")}]":
            depth -= 1
        elif char == "," and depth == 0:  # Fields separator, return only if depth is 0
            break
        end_pos += 1

    return fields_str[start_pos:end_pos].strip(), end_pos


def _parse_struct_fields(fields_str: str) -> list[Field]:
    """Parse a Struct fields string into a list of Field objects.

    Handles nested structures by tracking bracket depth.

    Arguments:
        fields_str: String representation of struct fields (e.g., "{'a': Int64, 'b': List(String)}")

    Returns:
        List of Field objects with deserialized dtypes

    Note:
        Assumes well-formed input from Narwhals dtype string representation.
    """
    if not fields_str:  # Empty struct case
        return []

    fields = []
    pos = 0

    while pos < len(fields_str):
        field_name, pos = _extract_field_name(fields_str, pos)

        # Skip whitespace after colon
        pos += sum(1 for _ in takewhile(str.isspace, fields_str[pos]))

        into_dtype, pos = _extract_field_dtype(fields_str, pos)
        dtype = deserialize_dtype(into_dtype)
        fields.append(Field(field_name, dtype))

    return fields
