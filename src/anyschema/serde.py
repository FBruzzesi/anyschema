from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Final, TypeVar

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
    Float16,
    Float32,
    Float64,
    Int8,
    Int16,
    Int32,
    Int64,
    Int128,
    List,
    Map,
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

from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from narwhals.dtypes import DType

__all__ = (
    "deserialize_dtype",
    "serialize_dtype",
)

T = TypeVar("T")

# Dtypes accepted as a bare name. Parametric ones (`Datetime`, `Duration`, `Decimal`) give their default instance.
_DTYPE_BY_NAME: Final[dict[str, DType]] = {
    "Binary": Binary(),
    "Boolean": Boolean(),
    "Categorical": Categorical(),
    "Date": Date(),
    "Datetime": Datetime(),
    "Decimal": Decimal(),
    "Duration": Duration(),
    "Float16": Float16(),
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
    "Unknown": Unknown(),
}


def serialize_dtype(dtype: DType) -> str:
    """Serialize a Narwhals dtype to a string that `deserialize_dtype` can read back.

    Arguments:
        dtype: The Narwhals dtype to serialize.

    Returns:
        The dtype repr, e.g. `"List(String)"`.

    Examples:
        >>> serialize_dtype(Int64())
        'Int64'
        >>> serialize_dtype(List(String()))
        'List(String)'
        >>> serialize_dtype(Datetime(time_unit="ms", time_zone="UTC"))
        "Datetime(time_unit='ms', time_zone='UTC')"
        >>> serialize_dtype(Struct({"a": Int64(), "b": String()}))
        "Struct({'a': Int64, 'b': String})"
        >>> serialize_dtype(Map(String(), List(Int64())))
        'Map(String, List(Int64))'
    """
    return str(dtype)


def deserialize_dtype(into_dtype: str) -> DType:
    """Deserialize a string produced by `serialize_dtype` back into a Narwhals dtype.

    The string is parsed with `ast.parse` and never evaluated. Each dtype accepts only its repr form, e.g.
    `Datetime(time_unit=..., time_zone=...)` with the keywords in that order. A bare name such as `"Datetime"` gives
    the default instance.

    Arguments:
        into_dtype: The dtype repr, e.g. `"Struct({'a': Int64, 'b': List(String)})"`.

    Returns:
        The Narwhals dtype.

    Raises:
        UnsupportedDTypeError: If `into_dtype` is not the repr of a supported dtype.

    Examples:
        >>> deserialize_dtype("Int64")
        Int64
        >>> deserialize_dtype("List(String)")
        List(String)
        >>> deserialize_dtype("Datetime(time_unit='ms', time_zone='UTC')")
        Datetime(time_unit='ms', time_zone='UTC')
        >>> deserialize_dtype("Datetime")
        Datetime(time_unit='us', time_zone=None)
        >>> deserialize_dtype("Map(String, List(Int64))")
        Map(String, List(Int64))
    """
    try:
        return _to_dtype(ast.parse(into_dtype, mode="eval").body)
    # `ast.parse` raises `MemoryError` when its stack overflows, e.g. on `"-" * 100_000 + "1"`.
    except (SyntaxError, MemoryError, RecursionError, TypeError, ValueError) as exc:
        msg = f"Unable to deserialize '{into_dtype}' into a Narwhals DType"
        raise UnsupportedDTypeError(msg) from exc


def _to_dtype(node: ast.expr) -> DType:
    """Match `node` against the repr of each dtype, raise `ValueError` if none fits."""
    match node:
        case ast.Name(id=name) if name in _DTYPE_BY_NAME:
            return _DTYPE_BY_NAME[name]

        case ast.Call(
            func=ast.Name(id="Datetime"),
            args=[],
            keywords=[
                ast.keyword(arg="time_unit", value=ast.Constant(value="ns" | "us" | "ms" | "s" as time_unit)),
                ast.keyword(arg="time_zone", value=ast.Constant(value=str() | None as time_zone)),
            ],
        ):
            return Datetime(time_unit=time_unit, time_zone=time_zone)

        case ast.Call(
            func=ast.Name(id="Duration"),
            args=[],
            keywords=[ast.keyword(arg="time_unit", value=ast.Constant(value="ns" | "us" | "ms" | "s" as time_unit))],
        ):
            return Duration(time_unit=time_unit)

        case ast.Call(
            func=ast.Name(id="Decimal"),
            args=[],
            keywords=[
                ast.keyword(arg="precision", value=ast.Constant(value=int() as precision)),
                ast.keyword(arg="scale", value=ast.Constant(value=int() as scale)),
            ],
        ):
            return Decimal(precision=precision, scale=scale)

        case ast.Call(
            func=ast.Name(id="Enum"),
            args=[],
            keywords=[ast.keyword(arg="categories", value=ast.List() as categories)],
        ):
            # `literal_eval` accepts negative numbers, e.g. `Enum(categories=[-1, 2])` from an int `enum.Enum`.
            return Enum(categories=ast.literal_eval(categories))

        case ast.Call(func=ast.Name(id="List"), args=[inner], keywords=[]):
            return List(_to_dtype(inner))

        case ast.Call(func=ast.Name(id="Map"), args=[key, value], keywords=[]):
            return Map(_to_dtype(key), _to_dtype(value))  # `Map(Object, ...)` raises `TypeError`

        case ast.Call(
            func=ast.Name(id="Array"),
            args=[inner],
            keywords=[ast.keyword(arg="shape", value=ast.Tuple(elts=dims))],
        ):
            return Array(_to_dtype(inner), shape=tuple(_to_constant(dim, int) for dim in dims))

        case ast.Call(
            func=ast.Name(id="Struct"),
            args=[ast.Dict(keys=field_names, values=field_dtypes)],
            keywords=[],
        ):
            return Struct(
                {
                    _to_constant(name, str): _to_dtype(dtype)
                    for name, dtype in zip(field_names, field_dtypes, strict=True)
                }
            )

        case _:
            msg = f"not a dtype: {ast.unparse(node)}"
            raise ValueError(msg)


def _to_constant(node: ast.expr | None, kind: type[T]) -> T:
    """Return the value of a `kind` constant node, raise `ValueError` otherwise."""
    match node:
        case ast.Constant(value=value) if isinstance(value, kind):
            return value
        case _:  # `None` is a `**` unpacking inside a dict
            msg = f"expected a {kind.__name__} constant"
            raise ValueError(msg)
