"""Tests for derived types similar to pydantic-extra-types.

This module tests that PyTypeStep correctly handles types that inherit
from basic Python types, similar to those in pydantic-extra-types library.

The derived types mimic pydantic-extra-types

References:
- https://docs.pydantic.dev/latest/api/pydantic_extra_types_country/
- https://docs.pydantic.dev/latest/api/pydantic_extra_types_phone_numbers/
- https://docs.pydantic.dev/latest/api/pydantic_extra_types_routing_numbers/
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import narwhals as nw
import pytest

from anyschema.parsers import ParserPipeline, PyTypeStep, UnionTypeStep


class EmailStr(str):
    __slots__ = ()


class PositiveInt(int): ...


class PositiveFloat(float): ...


class SecretBytes(bytes): ...


class PastDatetime(datetime): ...


class FutureDate(date): ...


class NonNegativeDecimal(Decimal): ...


class HttpMethod(str, Enum):
    """HTTP method enum."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class Priority(int, Enum):
    """Priority levels."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


@pytest.fixture(scope="module")
def parser_pipeline() -> ParserPipeline:
    """Create a parser pipeline with UnionTypeStep and PyTypeStep."""
    union_parser = UnionTypeStep()
    py_parser = PyTypeStep()
    return ParserPipeline([union_parser, py_parser])


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (EmailStr, nw.String()),
        (EmailStr | None, nw.String()),
        (list[EmailStr], nw.List(nw.String())),
        (PositiveInt, nw.Int64()),
        (list[PositiveInt], nw.List(nw.Int64())),
        (PositiveFloat, nw.Float64()),
        (tuple[PositiveFloat, PositiveFloat], nw.Array(nw.Float64(), shape=2)),
        (SecretBytes, nw.Binary()),
        (PastDatetime, nw.Datetime("us")),
        (FutureDate, nw.Date),
        (NonNegativeDecimal, nw.Decimal()),
        (HttpMethod, nw.Enum(HttpMethod)),
        (Priority, nw.Enum(Priority)),
    ],
)
def test_derived_types(parser_pipeline: ParserPipeline, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = parser_pipeline.parse(input_type, constraints=(), metadata={})
    assert result == expected
