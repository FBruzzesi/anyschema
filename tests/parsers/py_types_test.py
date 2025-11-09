from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, Union

import hypothesis.strategies as st
import narwhals as nw
import pytest
from hypothesis import given

from anyschema._parsers.py_types import parse_py_type_into_nw_dtype
from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from narwhals.dtypes import DType


class ColorEnum(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


@pytest.mark.parametrize(
    ("input_type", "output_type"),
    [
        # Basic Python types
        (int, nw.Int64()),
        (float, nw.Float64()),
        (str, nw.String()),
        (bool, nw.Boolean()),
        (bytes, nw.Binary()),
        (object, nw.Object()),
        (Decimal, nw.Decimal()),
        (type(None), None),
        (datetime, nw.Datetime("us")),
        (date, nw.Date()),
        (time, nw.Time()),
        (timedelta, nw.Duration()),
        (ColorEnum, nw.Enum(ColorEnum)),
        # Basic Python types or None
        (int | None, nw.Int64()),
        (None | float, nw.Float64()),
        (Optional[str], nw.String()),
        (Union[bool, None], nw.Boolean()),
        (Union[None, datetime], nw.Datetime()),
    ],
)
def test_parse_into_non_nested(input_type: type[object], output_type: DType) -> None:
    assert parse_py_type_into_nw_dtype(input_type) == output_type


@pytest.mark.parametrize(
    ("input_type", "output_type"),
    [
        (list[int], nw.List(nw.Int64())),
        (list[str | None], nw.List(nw.String())),
        (list[None | float], nw.List(nw.Float64())),
        (Sequence[bool], nw.List(nw.Boolean())),
        (tuple[datetime, ...], nw.List(nw.Datetime("us"))),
        (tuple[datetime | None, ...], nw.List(nw.Datetime("us"))),
        (Iterable[date | None], nw.List(nw.Date())),
        (list[int] | None, nw.List(nw.Int64())),  # TODO(FBruzzesi): Fix
        (list[list[int]], nw.List(nw.List(nw.Int64()))),
        (list[Sequence[int]], nw.List(nw.List(nw.Int64()))),
        (Iterable[tuple[int, ...]], nw.List(nw.List(nw.Int64()))),
    ],
)
def test_parse_into_list(input_type: type[object], output_type: DType) -> None:
    assert parse_py_type_into_nw_dtype(input_type) == output_type


def test_parse_list_without_args() -> None:
    """Test parsing of unparameterized list type returns None."""
    # Unparameterized list type is not supported by narwhals
    assert parse_py_type_into_nw_dtype(list) is None


def test_parse_sequence_without_args() -> None:
    """Test parsing of unparameterized Sequence type returns None."""
    # Unparameterized Sequence type is not supported by narwhals
    assert parse_py_type_into_nw_dtype(Sequence) is None
    assert parse_py_type_into_nw_dtype(Sequence[int]) == nw.List(nw.Int64())


def test_parse_sequence_str() -> None:
    """Test parsing of Sequence[str] type."""
    assert parse_py_type_into_nw_dtype(Sequence[str]) == nw.List(nw.String())


def test_parse_sequence_float() -> None:
    """Test parsing of Sequence[float] type."""
    assert parse_py_type_into_nw_dtype(Sequence[float]) == nw.List(nw.Float64())


# =====================
# Iterable Types
# =====================


def test_parse_iterable_without_args() -> None:
    """Test parsing of unparameterized Iterable type returns None."""
    # Unparameterized Iterable type is not supported by narwhals
    assert parse_py_type_into_nw_dtype(Iterable) is None


def test_parse_iterable_int() -> None:
    """Test parsing of Iterable[int] type."""
    assert parse_py_type_into_nw_dtype(Iterable[int]) == nw.List(nw.Int64())


def test_parse_iterable_str() -> None:
    """Test parsing of Iterable[str] type."""
    assert parse_py_type_into_nw_dtype(Iterable[str]) == nw.List(nw.String())


def test_parse_iterable_optional_int() -> None:
    """Test parsing of Iterable[int | None] type."""
    assert parse_py_type_into_nw_dtype(Iterable[int | None]) == nw.List(nw.Int64())


# =====================
# Tuple Types
# =====================


def test_parse_tuple_without_args() -> None:
    """Test parsing of unparameterized tuple type returns None."""
    # Unparameterized tuple type is not supported by narwhals
    assert parse_py_type_into_nw_dtype(tuple) is None


@given(n=st.integers(min_value=1, max_value=10))
def test_parse_tuple_homogeneous_int(n: int) -> None:  # noqa: ARG001
    """Test parsing of homogeneous tuple[int, ...] type with hypothesis."""
    # Parameter n is not used but required by hypothesis
    tuple_type = tuple[int, ...]
    result = parse_py_type_into_nw_dtype(tuple_type)
    assert result == nw.List(nw.Int64())


def test_parse_tuple_homogeneous_ellipsis_int() -> None:
    """Test parsing of tuple[int, ...] type."""
    assert parse_py_type_into_nw_dtype(tuple[int, ...]) == nw.List(nw.Int64())


def test_parse_tuple_homogeneous_ellipsis_str() -> None:
    """Test parsing of tuple[str, ...] type."""
    assert parse_py_type_into_nw_dtype(tuple[str, ...]) == nw.List(nw.String())


def test_parse_tuple_homogeneous_ellipsis_float() -> None:
    """Test parsing of tuple[float, ...] type."""
    assert parse_py_type_into_nw_dtype(tuple[float, ...]) == nw.List(nw.Float64())


def test_parse_tuple_fixed_size_int() -> None:
    """Test parsing of fixed-size tuple with int."""
    result = parse_py_type_into_nw_dtype(tuple[int, int, int])
    assert result == nw.Array(nw.Int64(), shape=3)


def test_parse_tuple_fixed_size_str() -> None:
    """Test parsing of fixed-size tuple with str."""
    result = parse_py_type_into_nw_dtype(tuple[str, str])
    assert result == nw.Array(nw.String(), shape=2)


def test_parse_tuple_fixed_size_float() -> None:
    """Test parsing of fixed-size tuple with float."""
    result = parse_py_type_into_nw_dtype(tuple[float, float, float, float])
    assert result == nw.Array(nw.Float64(), shape=4)


def test_parse_tuple_fixed_size_bool() -> None:
    """Test parsing of fixed-size tuple with bool."""
    result = parse_py_type_into_nw_dtype(tuple[bool, bool, bool, bool, bool])
    assert result == nw.Array(nw.Boolean(), shape=5)


@given(size=st.integers(min_value=1, max_value=5))
def test_parse_tuple_fixed_size_hypothesis(size: int) -> None:
    """Test parsing of fixed-size tuples with various sizes using hypothesis."""
    # Create tuple type dynamically based on size
    tuple_types = {
        1: tuple[int],
        2: tuple[int, int],
        3: tuple[int, int, int],
        4: tuple[int, int, int, int],
        5: tuple[int, int, int, int, int],
    }

    tuple_type = tuple_types[size]
    result = parse_py_type_into_nw_dtype(tuple_type)
    assert result == nw.Array(nw.Int64(), shape=size)


def test_parse_tuple_mixed_types_raises() -> None:
    """Test that tuple with mixed types raises UnsupportedDTypeError."""
    with pytest.raises(UnsupportedDTypeError, match="Tuple with mixed types is not supported"):
        parse_py_type_into_nw_dtype(tuple[int, str])


def test_parse_tuple_mixed_types_three_elements_raises() -> None:
    """Test that tuple with three mixed types raises UnsupportedDTypeError."""
    with pytest.raises(UnsupportedDTypeError, match="Tuple with mixed types is not supported"):
        parse_py_type_into_nw_dtype(tuple[int, str, float])


def test_parse_tuple_mixed_types_with_optional_raises() -> None:
    """Test that tuple with mixed types including optional raises UnsupportedDTypeError."""
    with pytest.raises(UnsupportedDTypeError, match="Tuple with mixed types is not supported"):
        parse_py_type_into_nw_dtype(tuple[int, int | None])


# =====================
# Edge Cases and Unsupported Types
# =====================


def test_parse_unsupported_custom_class() -> None:
    """Test parsing of unsupported custom class returns None."""

    class CustomClass:
        pass

    result = parse_py_type_into_nw_dtype(CustomClass)
    assert result is None


def test_parse_dict_returns_none() -> None:
    """Test parsing of dict type returns None."""
    result = parse_py_type_into_nw_dtype(dict)
    assert result is None


def test_parse_dict_with_args_returns_none() -> None:
    """Test parsing of dict[str, int] type returns None."""
    result = parse_py_type_into_nw_dtype(dict[str, int])
    assert result is None


def test_parse_set_returns_none() -> None:
    """Test parsing of set type returns None."""
    result = parse_py_type_into_nw_dtype(set)
    assert result is None


def test_parse_set_with_args_returns_none() -> None:
    """Test parsing of set[int] type returns None."""
    result = parse_py_type_into_nw_dtype(set[int])
    assert result is None


def test_parse_frozenset_returns_none() -> None:
    """Test parsing of frozenset type returns None."""
    result = parse_py_type_into_nw_dtype(frozenset)
    assert result is None


def test_parse_list_with_unsupported_inner_type_returns_none() -> None:
    """Test parsing of list with unsupported inner type returns None."""

    class CustomClass:
        pass

    result = parse_py_type_into_nw_dtype(list[CustomClass])
    assert result is None


def test_parse_optional_unsupported_type_returns_none() -> None:
    """Test parsing of unsupported type with None union returns None."""

    class CustomClass:
        pass

    result = parse_py_type_into_nw_dtype(CustomClass | None)
    assert result is None


# =====================
# Hypothesis-based Property Tests
# =====================


@given(
    base_type=st.sampled_from(
        [
            (int, nw.Int64()),
            (float, nw.Float64()),
            (str, nw.String()),
            (bool, nw.Boolean()),
            (bytes, nw.Binary()),
            (datetime, nw.Datetime("us")),
            (date, nw.Date()),
            (time, nw.Time()),
            (timedelta, nw.Duration()),
            (Decimal, nw.Decimal()),
        ]
    )
)
def test_parse_basic_types_hypothesis(base_type: tuple[type, Any]) -> None:
    """Test parsing of basic types using hypothesis."""
    py_type, expected_dtype = base_type
    result = parse_py_type_into_nw_dtype(py_type)
    assert result == expected_dtype


@given(
    base_type=st.sampled_from(
        [
            (int, nw.Int64()),
            (float, nw.Float64()),
            (str, nw.String()),
            (bool, nw.Boolean()),
            (datetime, nw.Datetime("us")),
            (date, nw.Date()),
        ]
    )
)
def test_parse_optional_types_hypothesis(base_type: tuple[type, Any]) -> None:
    """Test parsing of Optional types using hypothesis."""
    py_type, expected_dtype = base_type
    # Use type: ignore to suppress type checker warnings for runtime union types
    optional_type = py_type | None  # type: ignore[misc]
    result = parse_py_type_into_nw_dtype(optional_type)  # type: ignore[arg-type]
    assert result == expected_dtype


@given(
    base_type=st.sampled_from(
        [
            (int, nw.Int64()),
            (float, nw.Float64()),
            (str, nw.String()),
            (bool, nw.Boolean()),
            (datetime, nw.Datetime("us")),
            (date, nw.Date()),
        ]
    )
)
def test_parse_list_types_hypothesis(base_type: tuple[type, Any]) -> None:
    """Test parsing of list types using hypothesis."""
    py_type, expected_dtype = base_type
    list_type = list[py_type]
    result = parse_py_type_into_nw_dtype(list_type)
    assert result == nw.List(expected_dtype)


@given(
    base_type=st.sampled_from(
        [
            (int, nw.Int64()),
            (float, nw.Float64()),
            (str, nw.String()),
            (bool, nw.Boolean()),
        ]
    )
)
def test_parse_sequence_types_hypothesis(base_type: tuple[type, Any]) -> None:
    """Test parsing of Sequence types using hypothesis."""
    py_type, expected_dtype = base_type
    sequence_type = Sequence[py_type]
    result = parse_py_type_into_nw_dtype(sequence_type)
    assert result == nw.List(expected_dtype)


@given(
    base_type=st.sampled_from(
        [
            (int, nw.Int64()),
            (str, nw.String()),
            (float, nw.Float64()),
            (bool, nw.Boolean()),
        ]
    )
)
def test_parse_iterable_types_hypothesis(base_type: tuple[type, Any]) -> None:
    """Test parsing of Iterable types using hypothesis."""
    py_type, expected_dtype = base_type
    iterable_type = Iterable[py_type]
    result = parse_py_type_into_nw_dtype(iterable_type)
    assert result == nw.List(expected_dtype)


@given(
    base_type=st.sampled_from(
        [
            (int, nw.Int64()),
            (str, nw.String()),
            (float, nw.Float64()),
            (bool, nw.Boolean()),
        ]
    )
)
def test_parse_tuple_ellipsis_hypothesis(base_type: tuple[type, Any]) -> None:
    """Test parsing of tuple[T, ...] types using hypothesis."""
    py_type, expected_dtype = base_type
    # Create tuple with ellipsis dynamically
    tuple_type = tuple[py_type, ...]
    result = parse_py_type_into_nw_dtype(tuple_type)
    assert result == nw.List(expected_dtype)


# =====================
# Union Edge Cases
# =====================


def test_parse_union_int_none() -> None:
    """Test parsing of int | None type."""
    result = parse_py_type_into_nw_dtype(int | None)
    assert result == nw.Int64()


def test_parse_union_none_str() -> None:
    """Test parsing of None | str type."""
    result = parse_py_type_into_nw_dtype(None | str)
    assert result == nw.String()


def test_parse_union_float_none() -> None:
    """Test parsing of float | None type."""
    result = parse_py_type_into_nw_dtype(float | None)
    assert result == nw.Float64()


# =====================
# Enum Edge Cases
# =====================


def test_parse_enum_with_single_value() -> None:
    """Test parsing of Enum with one value."""

    class SingleEnum(Enum):
        ONLY = "only"

    result = parse_py_type_into_nw_dtype(SingleEnum)
    assert isinstance(result, nw.Enum)
    assert result == nw.Enum(SingleEnum)


def test_parse_enum_with_many_values() -> None:
    """Test parsing of Enum with many values."""

    class ManyValuesEnum(Enum):
        V1 = 1
        V2 = 2
        V3 = 3
        V4 = 4
        V5 = 5
        V6 = 6
        V7 = 7
        V8 = 8
        V9 = 9
        V10 = 10

    result = parse_py_type_into_nw_dtype(ManyValuesEnum)
    assert isinstance(result, nw.Enum)
    assert result == nw.Enum(ManyValuesEnum)


def test_parse_optional_enum() -> None:
    """Test parsing of Enum | None type."""

    class Status(Enum):
        ACTIVE = "active"
        INACTIVE = "inactive"

    result = parse_py_type_into_nw_dtype(Status | None)  # type: ignore[arg-type]
    assert isinstance(result, nw.Enum)
    assert result == nw.Enum(Status)


def test_parse_list_of_enum() -> None:
    """Test parsing of list[Enum] type."""

    class Priority(Enum):
        LOW = 1
        HIGH = 2

    result = parse_py_type_into_nw_dtype(list[Priority])
    assert result == nw.List(nw.Enum(Priority))


# =====================
# Triple Nested Types
# =====================


def test_parse_list_of_list_of_list_int() -> None:
    """Test parsing of deeply nested list type."""
    expected = nw.List(nw.List(nw.List(nw.Int64())))
    assert parse_py_type_into_nw_dtype(list[list[list[int]]]) == expected


def test_parse_optional_list_of_list_of_list_str() -> None:
    """Test parsing of list[list[list[str]]] | None type."""
    # When unwrapping optional of triple nested lists, returns List(List(String))
    expected = nw.List(nw.List(nw.String()))
    assert parse_py_type_into_nw_dtype(list[list[list[str]]] | None) == expected  # type: ignore[arg-type]


# =====================
# Object Type Special Cases
# =====================


def test_parse_object_type_explicitly() -> None:
    """Test explicit parsing of object type."""
    assert parse_py_type_into_nw_dtype(object) == nw.Object()


def test_parse_list_of_object() -> None:
    """Test parsing of list[object] type."""
    assert parse_py_type_into_nw_dtype(list[object]) == nw.List(nw.Object())


def test_parse_optional_object() -> None:
    """Test parsing of object | None type."""
    assert parse_py_type_into_nw_dtype(object | None) == nw.Object()  # type: ignore[arg-type]
