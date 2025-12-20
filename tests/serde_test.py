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

from anyschema.serde import deserialize_dtype, serialiaze_dtype


class Color(enum.Enum):
    BLUE = 1
    RED = 2


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
        (Decimal(), "Decimal"),
        (Duration(), "Duration(time_unit='us')"),
        (Duration(time_unit="ms"), "Duration(time_unit='ms')"),
        (Enum(Color), "Enum(categories=[1, 2])"),
        (Enum(["blue", "red"]), "Enum(categories=['blue', 'red'])"),
        (Float32(), "Float32"),
        (Float64(), "Float64"),
        (Int8(), "Int8"),
        (Int16(), "Int16"),
        (Int32(), "Int32"),
        (Int64(), "Int64"),
        (Int128(), "Int128"),
        (List(Int32()), "List(Int32)"),
        (List(Struct({"int": Int32(), "str": String()})), "List(Struct({'int': Int32, 'str': String}))"),
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
    result = serialiaze_dtype(dtype)
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
        ("Decimal", Decimal()),
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
    assert serialiaze_dtype(result) == into_dtype
