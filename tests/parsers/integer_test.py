from __future__ import annotations

from typing import Optional

import hypothesis.strategies as st
import narwhals as nw
from hypothesis import given
from pydantic import BaseModel
from pydantic import NegativeInt
from pydantic import NonNegativeInt
from pydantic import NonPositiveInt
from pydantic import PositiveInt
from pydantic import conint

from anyschema._parsers import model_to_nw_schema


def test_parse_to_integer() -> None:
    class IntegerModel(BaseModel):
        # python integer type
        py_int: int
        py_int_optional: Optional[int]  # noqa: UP007
        py_int_or_none: int | None
        py_none_or_int: None | int

        # pydantic NonNegativeInt type
        non_negative: NonNegativeInt
        non_negative_optional: Optional[NonNegativeInt]  # noqa: UP007
        non_negative_or_none: NonNegativeInt | None
        none_or_non_negative: None | NonNegativeInt

        # pydantic NonPositiveInt type
        non_positive: NonPositiveInt
        non_positive_optional: Optional[NonPositiveInt]  # noqa: UP007
        non_positive_or_none: NonPositiveInt | None
        none_or_non_positive: None | NonPositiveInt

        # pydantic PositiveInt type
        positive: PositiveInt
        positive_optional: Optional[PositiveInt]  # noqa: UP007
        positive_or_none: PositiveInt | None
        none_or_positive: None | PositiveInt

        # pydantic NegativeInt type
        negative: NegativeInt
        negative_optional: Optional[NegativeInt]  # noqa: UP007
        negative_or_none: NegativeInt | None
        none_or_negative: None | NegativeInt

    schema = model_to_nw_schema(IntegerModel)

    expected = {
        "py_int": nw.Int64(),
        "py_int_optional": nw.Int64(),
        "py_int_or_none": nw.Int64(),
        "py_none_or_int": nw.Int64(),
        "non_negative": nw.UInt64(),
        "non_negative_optional": nw.UInt64(),
        "non_negative_or_none": nw.UInt64(),
        "none_or_non_negative": nw.UInt64(),
        "non_positive": nw.Int64(),
        "non_positive_optional": nw.Int64(),
        "non_positive_or_none": nw.Int64(),
        "none_or_non_positive": nw.Int64(),
        "positive": nw.UInt64(),
        "positive_optional": nw.UInt64(),
        "positive_or_none": nw.UInt64(),
        "none_or_positive": nw.UInt64(),
        "negative": nw.Int64(),
        "negative_optional": nw.Int64(),
        "negative_or_none": nw.Int64(),
        "none_or_negative": nw.Int64(),
    }
    assert schema == expected


@given(lb=st.integers(-128, -2), ub=st.integers(2, 127))
def test_parse_to_int8(lb: int, ub: int) -> None:
    class Int8Model(BaseModel):
        x: conint(gt=lb, lt=ub)
        y: Optional[conint(ge=lb, lt=ub)]  # noqa: UP007
        z: conint(gt=lb, le=ub) | None
        w: None | conint(ge=lb, le=ub)

    schema = model_to_nw_schema(Int8Model)

    assert schema == {"x": nw.Int8(), "y": nw.Int8(), "z": nw.Int8(), "w": nw.Int8()}


@given(lb=st.integers(-32768, -129), ub=st.integers(129, 32767))
def test_parse_to_int16(lb: int, ub: int) -> None:
    class Int16Model(BaseModel):
        x: conint(gt=lb, lt=ub)
        y: Optional[conint(ge=lb, lt=ub)]  # noqa: UP007
        z: conint(gt=lb, le=ub) | None
        w: None | conint(ge=lb, le=ub)

    schema = model_to_nw_schema(Int16Model)

    assert schema == {"x": nw.Int16(), "y": nw.Int16(), "z": nw.Int16(), "w": nw.Int16()}


@given(lb=st.integers(-2147483648, -32769), ub=st.integers(32769, 2147483647))
def test_parse_to_int32(lb: int, ub: int) -> None:
    class Int32Model(BaseModel):
        x: conint(gt=lb, lt=ub)
        y: Optional[conint(ge=lb, lt=ub)]  # noqa: UP007
        z: conint(gt=lb, le=ub) | None
        w: None | conint(ge=lb, le=ub)

    schema = model_to_nw_schema(Int32Model)

    assert schema == {"x": nw.Int32(), "y": nw.Int32(), "z": nw.Int32(), "w": nw.Int32()}


@given(lb=st.integers(-9223372036854775808, -2147483649), ub=st.integers(2147483649, 9223372036854775808))
def test_parse_to_int64(lb: int, ub: int) -> None:
    class Int64Model(BaseModel):
        x: conint(gt=lb, lt=ub)
        y: Optional[conint(ge=lb, lt=ub)]  # noqa: UP007
        z: conint(gt=lb, le=ub) | None
        w: None | conint(ge=lb, le=ub)

    schema = model_to_nw_schema(Int64Model)

    assert schema == {"x": nw.Int64(), "y": nw.Int64(), "z": nw.Int64(), "w": nw.Int64()}


@given(ub=st.integers(1, 255))
def test_parse_to_uint8(ub: int) -> None:
    class UInt8Model(BaseModel):
        x: conint(gt=0, lt=ub)
        y: Optional[conint(ge=0, lt=ub)]  # noqa: UP007
        z: conint(gt=0, le=ub) | None
        w: None | conint(ge=0, le=ub)

    schema = model_to_nw_schema(UInt8Model)

    assert schema == {"x": nw.UInt8(), "y": nw.UInt8(), "z": nw.UInt8(), "w": nw.UInt8()}


@given(ub=st.integers(257, 65535))
def test_parse_to_uint16(ub: int) -> None:
    class UInt16Model(BaseModel):
        x: conint(gt=0, lt=ub)
        y: Optional[conint(ge=0, lt=ub)]  # noqa: UP007
        z: conint(gt=0, le=ub) | None
        w: None | conint(ge=0, le=ub)

    schema = model_to_nw_schema(UInt16Model)

    assert schema == {"x": nw.UInt16(), "y": nw.UInt16(), "z": nw.UInt16(), "w": nw.UInt16()}


@given(ub=st.integers(65537, 4294967295))
def test_parse_to_uint32(ub: int) -> None:
    class UInt32Model(BaseModel):
        x: conint(gt=0, lt=ub)
        y: Optional[conint(ge=0, lt=ub)]  # noqa: UP007
        z: conint(gt=0, le=ub) | None
        w: None | conint(ge=0, le=ub)

    schema = model_to_nw_schema(UInt32Model)

    assert schema == {"x": nw.UInt32(), "y": nw.UInt32(), "z": nw.UInt32(), "w": nw.UInt32()}


@given(ub=st.integers(4294967297, 18446744073709551615))
def test_parse_to_uint64(ub: int) -> None:
    class UInt64Model(BaseModel):
        x: conint(gt=0, lt=ub)
        y: Optional[conint(ge=0, lt=ub)]  # noqa: UP007
        z: conint(gt=0, le=ub) | None
        w: None | conint(ge=0, le=ub)

    schema = model_to_nw_schema(UInt64Model)

    assert schema == {"x": nw.UInt64(), "y": nw.UInt64(), "z": nw.UInt64(), "w": nw.UInt64()}


@given(value=st.integers(9223372036854775808))
def test_parse_to_int64_from_unbounded(value: int) -> None:
    class UnboundedModel(BaseModel):
        x: conint(lt=value)

    schema = model_to_nw_schema(UnboundedModel)

    assert schema == {"x": nw.Int64()}
