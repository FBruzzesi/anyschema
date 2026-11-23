from __future__ import annotations

import sys
from collections import Counter, OrderedDict, defaultdict
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum, IntEnum, IntFlag
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Interface
from pathlib import Path, PurePosixPath
from types import NoneType
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple, TypedDict
from typing import Mapping as TypingMapping
from typing import Sequence as TypingSequence
from uuid import UUID

import narwhals as nw
import pytest
import typing_extensions
from annotated_types import Ge, Le

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers import ParserPipeline, PyTypeStep, UnionTypeStep, make_pipeline


class Color(Enum):
    """Example enum for testing."""

    RED = 1
    GREEN = 2
    BLUE = 3


class MixedEnum(Enum):
    NUMBER = 1
    TEXT = "text"


class EmptyEnum(Enum):
    pass


class Status(Enum):
    """Another enum for testing."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class HttpStatus(IntEnum):
    OK = 200
    NOT_FOUND = 404


class Permission(IntFlag):
    READ = 1
    WRITE = 2


class Ratio(float, Enum):
    HALF = 0.5


class CustomClass:
    pass


@pytest.fixture(scope="module")
def py_type_parser() -> PyTypeStep:
    """Create a PyTypeStep instance with pipeline set."""
    union_parser = UnionTypeStep()
    py_parser = PyTypeStep()
    _ = ParserPipeline([union_parser, py_parser])
    return py_parser


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (int, nw.Int64()),
        (float, nw.Float64()),
        (str, nw.String()),
        (bool, nw.Boolean()),
        (datetime, nw.Datetime("us")),
        (date, nw.Date()),
        (timedelta, nw.Duration()),
        (time, nw.Time()),
        (Decimal, nw.Decimal()),
        (bytes, nw.Binary()),
        (UUID, nw.String()),
        (Path, nw.String()),
        (PurePosixPath, nw.String()),
        (IPv4Address, nw.String()),
        (IPv6Address, nw.String()),
        (IPv6Interface, nw.String()),
        (IPv4Network, nw.String()),
        (object, nw.Object()),
        (Any, nw.Object()),
        (typing_extensions.Any, nw.Object()),
        (Status, nw.Enum(Status)),
        (Color, nw.UInt8()),
        (HttpStatus, nw.UInt16()),
        (Permission, nw.Int64()),
        (Ratio, nw.Float64()),
        (Literal["red", "green", "blue"], nw.Enum(("red", "green", "blue"))),
        (Literal[1, 2, 3], nw.UInt8()),
        (Literal[-1, 300], nw.Int16()),
        (Literal["active", "inactive"], nw.Enum(("active", "inactive"))),
        (Literal[True, False], nw.Boolean()),
        (Literal["a", None], nw.Enum(("a",))),  # noqa: PYI061
        (Literal[Status.ACTIVE], nw.Enum(Status)),
    ],
)
def test_parse_non_nested(py_type_parser: PyTypeStep, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = py_type_parser.parse(input_type, (), {})
    assert result == expected


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (list[int], nw.List(nw.Int64())),
        (list[str], nw.List(nw.String())),
        (list[float], nw.List(nw.Float64())),
        (list[bool], nw.List(nw.Boolean())),
        (list[list[int]], nw.List(nw.List(nw.Int64()))),
        (list[Any], nw.List(nw.Object())),
        (list[tuple[int, int]], nw.List(nw.Array(nw.Int64(), shape=2))),
        (Sequence[int], nw.List(nw.Int64())),
        (Sequence[str | None], nw.List(nw.String())),
        (Iterable[int], nw.List(nw.Int64())),
        (Iterable[str], nw.List(nw.String())),
        (Sequence[Sequence[str]], nw.List(nw.List(nw.String()))),
        (tuple[int | None, ...], nw.List(nw.Int64())),
        (tuple[int, int, int], nw.Array(nw.Int64(), shape=3)),
        (tuple[str, str], nw.Array(nw.String(), shape=2)),
        (list, nw.List(nw.Object())),
        (tuple, nw.List(nw.Object())),
        (Sequence, nw.List(nw.Object())),
        (Iterable, nw.List(nw.Object())),
        (List, nw.List(nw.Object())),
        (TypingSequence, nw.List(nw.Object())),
        (Tuple, nw.List(nw.Object())),
    ],
)
def test_parse_nested(py_type_parser: PyTypeStep, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = py_type_parser.parse(input_type, (), {})
    assert result == expected


@pytest.mark.parametrize("input_type", [tuple[int, str], tuple[int, str, float]])
def test_parse_heterogeneous_tuple_raises(py_type_parser: PyTypeStep, input_type: Any) -> None:
    with pytest.raises(UnsupportedDTypeError, match="Tuple with mixed types is not supported"):
        py_type_parser.parse(input_type, (), {})


@pytest.mark.parametrize(
    "input_type",
    [MixedEnum, EmptyEnum, Literal["a", 1], Literal[1, True], Literal[None]],  # noqa: PYI061
)
def test_parse_enum_values_without_single_type_raises(py_type_parser: PyTypeStep, input_type: Any) -> None:
    with pytest.raises(UnsupportedDTypeError, match="must be non-empty and of a single type"):
        py_type_parser.parse(input_type, (), {})


@pytest.mark.parametrize(("input_type", "expected"), [(int, nw.Int64()), (list[int], nw.List(nw.Int64()))])
def test_parse_with_metadata(py_type_parser: PyTypeStep, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = py_type_parser.parse(input_type, constraints=("some", "constraints"), metadata={"key": "value"})
    assert result == expected


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({}, nw.Datetime("us")),
        ({"anyschema": {"time_unit": "ms"}}, nw.Datetime("ms")),
        ({"anyschema": {"time_unit": "ns"}}, nw.Datetime("ns")),
        ({"anyschema": {"time_zone": "UTC"}}, nw.Datetime("us", time_zone="UTC")),
        ({"anyschema": {"time_zone": "Europe/Rome"}}, nw.Datetime("us", time_zone="Europe/Rome")),
        ({"anyschema": {"time_unit": "ms", "time_zone": "UTC"}}, nw.Datetime("ms", time_zone="UTC")),
        (
            {"anyschema": {"time_unit": "ns", "time_zone": "America/New_York"}},
            nw.Datetime("ns", time_zone="America/New_York"),
        ),
    ],
)
def test_parse_datetime_with_time_metadata(
    py_type_parser: PyTypeStep, metadata: dict[str, Any], expected: nw.dtypes.DType
) -> None:
    """Test that datetime parses correctly with anyschema/time_zone and anyschema/time_unit metadata."""
    result = py_type_parser.parse(datetime, constraints=(), metadata=metadata)
    assert result == expected


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({}, nw.Decimal()),
        ({"anyschema": {"precision": 10}}, nw.Decimal(precision=10)),
        ({"anyschema": {"scale": 2}}, nw.Decimal(scale=2)),
        ({"anyschema": {"precision": 10, "scale": 2}}, nw.Decimal(precision=10, scale=2)),
        ({"anyschema": {"precision": 38, "scale": 0}}, nw.Decimal(precision=38, scale=0)),
    ],
)
def test_parse_decimal_with_precision_scale_metadata(
    py_type_parser: PyTypeStep, metadata: dict[str, Any], expected: nw.dtypes.DType
) -> None:
    """Test that Decimal parses correctly with anyschema/precision and anyschema/scale metadata."""
    result = py_type_parser.parse(Decimal, constraints=(), metadata=metadata)
    assert result == expected


@pytest.mark.parametrize("input_type", [CustomClass, NoneType, set[int], set[CustomClass], frozenset])
def test_unsupported_type(py_type_parser: PyTypeStep, input_type: Any) -> None:
    result = py_type_parser.parse(input_type, (), {})
    assert result is None


class PersonTypedDict(TypedDict):
    """Example TypedDict for testing."""

    name: str
    age: int


class AddressTypedDict(TypedDict):
    """Nested TypedDict for testing."""

    street: str
    city: str
    zipcode: int


class PersonWithAddressTypedDict(TypedDict):
    """TypedDict with nested TypedDict for testing."""

    name: str
    address: AddressTypedDict


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        # Bare mappings -> empty Struct
        (dict, nw.Struct([])),
        (Dict, nw.Struct([])),
        (TypingMapping, nw.Struct([])),
        (Mapping, nw.Struct([])),
        (MutableMapping, nw.Struct([])),
        (Counter, nw.Struct([])),
        # Typed mappings -> Map
        (dict[str, int], nw.Map(nw.String(), nw.Int64())),
        (Dict[str, int], nw.Map(nw.String(), nw.Int64())),
        (Mapping[str, int], nw.Map(nw.String(), nw.Int64())),
        (MutableMapping[str, int], nw.Map(nw.String(), nw.Int64())),
        (OrderedDict[str, int], nw.Map(nw.String(), nw.Int64())),
        (defaultdict[str, int], nw.Map(nw.String(), nw.Int64())),
        (Counter[str], nw.Map(nw.String(), nw.Int64())),
        (dict[str, Any], nw.Map(nw.String(), nw.Object())),
        (dict[str, int | None], nw.Map(nw.String(), nw.Int64())),
        (dict[str, dict[int, list[float]]], nw.Map(nw.String(), nw.Map(nw.Int64(), nw.List(nw.Float64())))),
        (
            dict[str, PersonTypedDict],
            nw.Map(
                nw.String(),
                nw.Struct([nw.Field(name="name", dtype=nw.String()), nw.Field(name="age", dtype=nw.Int64())]),
            ),
        ),
        # TypedDict -> Struct with fields
        (
            PersonTypedDict,
            nw.Struct([nw.Field(name="name", dtype=nw.String()), nw.Field(name="age", dtype=nw.Int64())]),
        ),
        (
            AddressTypedDict,
            nw.Struct(
                [
                    nw.Field(name="street", dtype=nw.String()),
                    nw.Field(name="city", dtype=nw.String()),
                    nw.Field(name="zipcode", dtype=nw.Int64()),
                ]
            ),
        ),
        # Nested TypedDict
        (
            PersonWithAddressTypedDict,
            nw.Struct(
                [
                    nw.Field(name="name", dtype=nw.String()),
                    nw.Field(
                        name="address",
                        dtype=nw.Struct(
                            [
                                nw.Field(name="street", dtype=nw.String()),
                                nw.Field(name="city", dtype=nw.String()),
                                nw.Field(name="zipcode", dtype=nw.Int64()),
                            ]
                        ),
                    ),
                ]
            ),
        ),
    ],
)
def test_parse_dict_types(py_type_parser: PyTypeStep, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = py_type_parser.parse(input_type, (), {})
    assert result == expected


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        # Key and value are narrowed by their own constraints
        (dict[Annotated[int, Ge(0)], Annotated[int, Le(100)]], nw.Map(nw.UInt64(), nw.Int64())),
        # Field-level constraints describe the mapping, not its items
        (Annotated[dict[str, int], Ge(0)], nw.Map(nw.String(), nw.Int64())),
    ],
)
def test_parse_mapping_constraints(input_type: Any, expected: nw.dtypes.DType) -> None:
    assert make_pipeline().parse(input_type, (), {}) == expected


@pytest.mark.parametrize(
    ("input_type", "nullable"),
    [(dict[str, int | None], False), (dict[str, int] | None, True), (Optional[dict[str, int]], True)],
)
def test_parse_mapping_field_nullability(input_type: Any, *, nullable: bool) -> None:
    field = make_pipeline().parse_into_field("a", input_type, (), {})
    assert (field.dtype, field.nullable) == (nw.Map(nw.String(), nw.Int64()), nullable)


@pytest.mark.parametrize(
    ("input_type", "match"),
    [
        (dict[str | None, int], "Map keys cannot be null"),
        (dict[Optional[str], int], "Map keys cannot be null"),
        (dict[Annotated[str | None, "meta"], int], "Map keys cannot be null"),
        (dict[Literal["a", None], int], "Map keys cannot be null"),  # noqa: PYI061
        (dict[Any, int], "Map keys cannot be Object"),
        (dict[object, int], "Map keys cannot be Object"),
    ],
)
def test_parse_mapping_unsupported_key_raises(input_type: Any, match: str) -> None:
    pipeline = make_pipeline()
    with pytest.raises(UnsupportedDTypeError, match=match):
        pipeline.parse(input_type, (), {})


@dataclass
class AddressDataclass:
    street: str
    zipcode: int


@dataclass
class PersonWithAddressDataclass:
    name: str
    address: AddressDataclass
    past_addresses: list[AddressDataclass]


class EnumWithDataclassMixin(AddressDataclass, Enum):
    HOME = "Main St", 1


ADDRESS_STRUCT = nw.Struct([nw.Field(name="street", dtype=nw.String()), nw.Field(name="zipcode", dtype=nw.Int64())])


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (AddressDataclass, ADDRESS_STRUCT),
        (
            PersonWithAddressDataclass,
            nw.Struct(
                [
                    nw.Field(name="name", dtype=nw.String()),
                    nw.Field(name="address", dtype=ADDRESS_STRUCT),
                    nw.Field(name="past_addresses", dtype=nw.List(ADDRESS_STRUCT)),
                ]
            ),
        ),
        # A mixin enum gets the dtype of its values. Python 3.10 keeps the raw `("Main St", 1)` tuple as the value.
        (EnumWithDataclassMixin, ADDRESS_STRUCT if sys.version_info >= (3, 11) else nw.List(nw.Object())),
    ],
)
def test_parse_dataclass(py_type_parser: PyTypeStep, input_type: Any, expected: nw.dtypes.DType) -> None:
    assert py_type_parser.parse(input_type, (), {}) == expected
