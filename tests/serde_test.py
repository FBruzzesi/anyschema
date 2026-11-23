from __future__ import annotations

import enum

import pytest
from narwhals.dtypes import (
    Array,
    Binary,
    Boolean,
    Categorical,
    Date,
    Datetime,
    Decimal,
    DType,
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
from anyschema.serde import deserialize_dtype, serialize_dtype


class Color(enum.Enum):
    BLUE = 1
    RED = 2


class Sign(enum.Enum):
    NEG = -1
    POS = 2


@pytest.mark.parametrize(
    ("dtype", "expected"),
    [
        (Array(Int32(), 2), "Array(Int32, shape=(2,))"),
        (Array(Int32(), (2, 3)), "Array(Int32, shape=(2, 3))"),
        (Array(List(Int32()), (2, 3)), "Array(List(Int32), shape=(2, 3))"),
        (Binary(), "Binary"),
        (Boolean(), "Boolean"),
        (Categorical(), "Categorical"),
        (Date(), "Date"),
        (Datetime(), "Datetime(time_unit='us', time_zone=None)"),
        (Datetime(time_unit="ms"), "Datetime(time_unit='ms', time_zone=None)"),
        (Datetime(time_zone="UTC"), "Datetime(time_unit='us', time_zone='UTC')"),
        (Datetime("s", "Europe/Berlin"), "Datetime(time_unit='s', time_zone='Europe/Berlin')"),
        (Decimal(), "Decimal(precision=38, scale=0)"),
        (Decimal(precision=10, scale=2), "Decimal(precision=10, scale=2)"),
        (Decimal(precision=5), "Decimal(precision=5, scale=0)"),
        (Decimal(scale=3), "Decimal(precision=38, scale=3)"),
        (Duration(), "Duration(time_unit='us')"),
        (Duration(time_unit="ms"), "Duration(time_unit='ms')"),
        (Enum(Color), "Enum(categories=[1, 2])"),
        (Enum(["blue", "red"]), "Enum(categories=['blue', 'red'])"),
        (Float16(), "Float16"),
        (Float32(), "Float32"),
        (Float64(), "Float64"),
        (Int8(), "Int8"),
        (Int16(), "Int16"),
        (Int32(), "Int32"),
        (Int64(), "Int64"),
        (Int128(), "Int128"),
        (List(Int32()), "List(Int32)"),
        (List(Struct({"int": Int32(), "str": String()})), "List(Struct({'int': Int32, 'str': String}))"),
        (Map(String(), Int64()), "Map(String, Int64)"),
        (Map(String(), Map(Int8(), List(Float16()))), "Map(String, Map(Int8, List(Float16)))"),
        (Map(String(), Struct({"a": Int64()})), "Map(String, Struct({'a': Int64}))"),
        (List(Map(String(), Int64())), "List(Map(String, Int64))"),
        (Object(), "Object"),
        (String(), "String"),
        (Struct({}), "Struct({})"),
        (Struct({"int": Int32(), "str": String()}), "Struct({'int': Int32, 'str': String})"),
        (
            Struct({"lst": List(Int32()), "arr": Array(Int16(), (3, 2))}),
            "Struct({'lst': List(Int32), 'arr': Array(Int16, shape=(3, 2))})",
        ),
        (
            Struct({"struct": Struct({"enum": Enum(["blue", "red"])})}),
            "Struct({'struct': Struct({'enum': Enum(categories=['blue', 'red'])})})",
        ),
        (Time(), "Time"),
        (UInt8(), "UInt8"),
        (UInt16(), "UInt16"),
        (UInt32(), "UInt32"),
        (UInt64(), "UInt64"),
        (UInt128(), "UInt128"),
        (Unknown(), "Unknown"),
    ],
)
def test_serialize(dtype: DType, expected: str) -> None:
    result = serialize_dtype(dtype)
    assert result == expected

    # round-trip
    assert deserialize_dtype(result) == dtype


@pytest.mark.parametrize(
    ("into_dtype", "expected"),
    [
        ("Array(Int32, shape=(2,))", Array(Int32(), 2)),
        ("Array(Int32, shape=(2, 3))", Array(Int32(), (2, 3))),
        ("Array(List(Int32), shape=(2, 3))", Array(List(Int32()), (2, 3))),
        ("Binary", Binary()),
        ("Boolean", Boolean()),
        ("Categorical", Categorical()),
        ("Date", Date()),
        ("Datetime(time_unit='us', time_zone=None)", Datetime()),
        ("Datetime(time_unit='ms', time_zone=None)", Datetime(time_unit="ms")),
        ("Datetime(time_unit='us', time_zone='UTC')", Datetime(time_zone="UTC")),
        ("Datetime(time_unit='s', time_zone='Europe/Berlin')", Datetime("s", "Europe/Berlin")),
        ("Decimal(precision=38, scale=0)", Decimal()),
        ("Decimal(precision=10, scale=2)", Decimal(precision=10, scale=2)),
        ("Decimal(precision=5, scale=0)", Decimal(precision=5)),
        ("Decimal(precision=38, scale=3)", Decimal(scale=3)),
        ("Duration(time_unit='us')", Duration()),
        ("Duration(time_unit='ms')", Duration(time_unit="ms")),
        ("Enum(categories=[1, 2])", Enum(Color)),
        ("Enum(categories=['blue', 'red'])", Enum(["blue", "red"])),
        ("Float32", Float32()),
        ("Float64", Float64()),
        ("Int8", Int8()),
        ("Int16", Int16()),
        ("Int32", Int32()),
        ("Int64", Int64()),
        ("Int128", Int128()),
        ("List(Int32)", List(Int32())),
        ("List(Struct({'int': Int32, 'str': String}))", List(Struct({"int": Int32(), "str": String()}))),
        ("Object", Object()),
        ("String", String()),
        ("Struct({})", Struct({})),
        ("Struct({'int': Int32, 'str': String})", Struct({"int": Int32(), "str": String()})),
        (
            "Struct({'lst': List(Int32), 'arr': Array(Int16, shape=(3, 2))})",
            Struct({"lst": List(Int32()), "arr": Array(Int16(), (3, 2))}),
        ),
        (
            "Struct({'struct': Struct({'enum': Enum(categories=['blue', 'red'])})})",
            Struct({"struct": Struct({"enum": Enum(["blue", "red"])})}),
        ),
        ("Time", Time()),
        ("UInt8", UInt8()),
        ("UInt16", UInt16()),
        ("UInt32", UInt32()),
        ("UInt64", UInt64()),
        ("UInt128", UInt128()),
        ("Unknown", Unknown()),
    ],
)
def test_deserialize(into_dtype: str, expected: DType) -> None:
    result = deserialize_dtype(into_dtype)
    assert result == expected

    # round-trip
    assert serialize_dtype(result) == into_dtype


@pytest.mark.parametrize(
    ("into_dtype", "expected"),
    [
        ("""Struct({"it's": Int64})""", Struct({"it's": Int64()})),
        ("Struct({'x': Enum(categories=['a)']), 'y': Int8})", Struct({"x": Enum(["a)"]), "y": Int8()})),
        ("Enum(categories=[-1, 2])", Enum(Sign)),
        ("Datetime", Datetime()),
        ("Duration", Duration()),
        ("Decimal", Decimal()),
    ],
)
def test_deserialize_extra_valid_inputs(into_dtype: str, expected: DType) -> None:
    assert deserialize_dtype(into_dtype) == expected


@pytest.mark.parametrize(
    "into_dtype",
    [
        "InvalidType",
        "List(",
        "not a dtype at all",
        "",
        "__import__('os').system('true')",
        "().__class__",
        "Int64.__class__",
        "Foo(1)",
        "List(String",
        "Datetime(time_unit='ms')",
        "Datetime(time_unit='bogus', time_zone=None)",
        "Duration(time_unit='bogus')",
        "Int64(1)",
        "Struct",
        "DType",
        "NumericType",
        "Field('a', Int64)",
        "List(**{'inner': Int64})",
        "Struct({**{'a': Int64}})",
        "List(*[Int64])",
        "List[Int64]",
        "lambda: Int64",
        "1",
        "[Int64]",
        "List(1)",
        "Array('a', shape=(2,))",
        "Array(Int32, shape=(1.5,))",
        "Struct({'a': 1})",
        "Struct({1: Int64})",
        "Map(String)",
        "Map(key=String, value=Int64)",
        "Map(Object, Int64)",
        "Map(String, 1)",
        "Int64\x00",
        "List(" * 10_000 + "Int64" + ")" * 10_000,
        "-" * 100_000 + "1",
    ],
)
def test_deserialize_invalid_dtype_raises(into_dtype: str) -> None:
    with pytest.raises(UnsupportedDTypeError, match="Unable to deserialize"):
        deserialize_dtype(into_dtype)
