from __future__ import annotations

import hypothesis.strategies as st
import narwhals as nw
from hypothesis import given
from pydantic import BaseModel
from pydantic import NonNegativeInt
from pydantic import PositiveInt
from pydantic import conint

from anyschema._parsers import model_to_nw_schema


def test_parse_python_int() -> None:
    class PythonInt(BaseModel):
        py_int: int

    schema = model_to_nw_schema(PythonInt)

    assert schema == {"py_int": nw.Int64()}


def test_parse_pydantic_integer() -> None:
    class PydanticInt(BaseModel):
        positive_int: PositiveInt
        non_negative_int: NonNegativeInt

    schema = model_to_nw_schema(PydanticInt)

    assert schema == {"positive_int": nw.UInt64(), "non_negative_int": nw.UInt64()}


@given(lb=st.integers(-128, -2), ub=st.integers(2, 127))
def test_parse_to_int8(lb: int, ub: int) -> None:
    class Int8Model(BaseModel):
        x: conint(gt=lb, lt=ub)
        y: conint(gt=lb, le=ub)
        z: conint(ge=lb, lt=ub)
        w: conint(ge=lb, le=ub)

    schema = model_to_nw_schema(Int8Model)

    assert schema == {"x": nw.Int8(), "y": nw.Int8(), "z": nw.Int8(), "w": nw.Int8()}


@given(lb=st.integers(-32768, -129), ub=st.integers(129, 32767))
def test_parse_to_int16(lb: int, ub: int) -> None:
    class Int16Model(BaseModel):
        x: conint(gt=lb, lt=ub)
        y: conint(gt=lb, le=ub)
        z: conint(ge=lb, lt=ub)
        w: conint(ge=lb, le=ub)

    schema = model_to_nw_schema(Int16Model)

    assert schema == {"x": nw.Int16(), "y": nw.Int16(), "z": nw.Int16(), "w": nw.Int16()}


@given(lb=st.integers(-2147483648, -32769), ub=st.integers(32769, 2147483647))
def test_parse_to_int32(lb: int, ub: int) -> None:
    class Int32Model(BaseModel):
        x: conint(gt=lb, lt=ub)
        y: conint(gt=lb, le=ub)
        z: conint(ge=lb, lt=ub)
        w: conint(ge=lb, le=ub)

    schema = model_to_nw_schema(Int32Model)

    assert schema == {"x": nw.Int32(), "y": nw.Int32(), "z": nw.Int32(), "w": nw.Int32()}


@given(lb=st.integers(-9223372036854775808, -2147483649), ub=st.integers(2147483649, 9223372036854775808))
def test_parse_to_int64(lb: int, ub: int) -> None:
    class Int64Model(BaseModel):
        x: conint(gt=lb, lt=ub)
        y: conint(gt=lb, le=ub)
        z: conint(ge=lb, lt=ub)
        w: conint(ge=lb, le=ub)

    schema = model_to_nw_schema(Int64Model)

    assert schema == {"x": nw.Int64(), "y": nw.Int64(), "z": nw.Int64(), "w": nw.Int64()}


@given(ub=st.integers(1, 255))
def test_parse_to_uint8(ub: int) -> None:
    class UInt8Model(BaseModel):
        x: conint(gt=0, lt=ub)
        y: conint(gt=0, le=ub)

    schema = model_to_nw_schema(UInt8Model)

    assert schema == {"x": nw.UInt8(), "y": nw.UInt8()}


@given(ub=st.integers(257, 65535))
def test_parse_to_uint16(ub: int) -> None:
    class UInt16Model(BaseModel):
        x: conint(gt=0, lt=ub)
        y: conint(gt=0, le=ub)

    schema = model_to_nw_schema(UInt16Model)

    assert schema == {"x": nw.UInt16(), "y": nw.UInt16()}


@given(ub=st.integers(65537, 4294967295))
def test_parse_to_uint32(ub: int) -> None:
    class UInt32Model(BaseModel):
        x: conint(gt=0, lt=ub)
        y: conint(gt=0, le=ub)

    schema = model_to_nw_schema(UInt32Model)

    assert schema == {"x": nw.UInt32(), "y": nw.UInt32()}


@given(ub=st.integers(4294967297, 18446744073709551615))
def test_parse_to_uint64(ub: int) -> None:
    class UInt64Model(BaseModel):
        x: conint(gt=0, lt=ub)
        y: conint(gt=0, le=ub)

    schema = model_to_nw_schema(UInt64Model)

    assert schema == {"x": nw.UInt64(), "y": nw.UInt64()}


@given(value=st.integers(9223372036854775808))
def test_parse_to_int64_from_unbounded(value: int) -> None:
    class UnboundedModel(BaseModel):
        x: conint(lt=value)

    schema = model_to_nw_schema(UnboundedModel)

    assert schema == {"x": nw.Int64()}
