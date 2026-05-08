"""Tests using actual pydantic-extra-types to verify derived type handling.

This module tests that PyTypeStep works with real types from the pydantic-extra-types library.
Note that some pydantic-extra-types require additional dependencies (like pycountry, phonenumbers).

References:
- https://docs.pydantic.dev/latest/api/pydantic_extra_types_country/
- https://docs.pydantic.dev/latest/api/pydantic_extra_types_phone_numbers/
- https://docs.pydantic.dev/latest/api/pydantic_extra_types_coordinate/
- https://docs.pydantic.dev/latest/api/pydantic_extra_types_color/
"""

from __future__ import annotations

from typing import Any

import narwhals as nw
import pytest
from pydantic_extra_types.color import Color
from pydantic_extra_types.coordinate import Latitude, Longitude
from pydantic_extra_types.country import (
    CountryAlpha2,
    CountryAlpha3,
    CountryNumericCode,
    CountryShortName,
)
from pydantic_extra_types.currency_code import Currency
from pydantic_extra_types.isbn import ISBN
from pydantic_extra_types.language_code import LanguageAlpha2, LanguageName
from pydantic_extra_types.mac_address import MacAddress
from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic_extra_types.timezone_name import TimeZoneName

from anyschema.parsers import ParserPipeline, PyTypeStep, UnionTypeStep
from anyschema.parsers.pydantic import PydanticTypeStep


@pytest.fixture(scope="module")
def py_type_parser() -> PyTypeStep:
    """Create a PyTypeStep instance with pipeline set."""
    union_parser = UnionTypeStep()
    py_parser = PyTypeStep()
    _ = ParserPipeline([union_parser, py_parser])
    return py_parser


@pytest.fixture(scope="module")
def pydantic_parser() -> PydanticTypeStep:
    """Create a PydanticTypeStep instance with pipeline set."""
    pydantic_parser = PydanticTypeStep()
    py_parser = PyTypeStep()
    _ = ParserPipeline([pydantic_parser, py_parser])
    return pydantic_parser


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        # coordinate
        (Latitude, nw.Float64()),
        (Longitude, nw.Float64()),
        (list[Latitude], nw.List(nw.Float64())),
        (list[list[Latitude]], nw.List(nw.List(nw.Float64()))),
        (tuple[Longitude, Longitude], nw.Array(nw.Float64(), shape=2)),
        (tuple[Latitude, Latitude, Latitude], nw.Array(nw.Float64(), shape=3)),
        # country
        (CountryAlpha2, nw.String()),
        (CountryAlpha3, nw.String()),
        (CountryNumericCode, nw.String()),
        (CountryShortName, nw.String()),
        (list[CountryAlpha2], nw.List(nw.String())),
        (list[list[CountryAlpha2]], nw.List(nw.List(nw.String()))),
        # phone number
        (PhoneNumber, nw.String()),
        (list[PhoneNumber], nw.List(nw.String())),
        (tuple[PhoneNumber, PhoneNumber, PhoneNumber], nw.Array(nw.String(), shape=3)),
        # currency
        (Currency, nw.String()),
        # isbn
        (ISBN, nw.String()),
        # language
        (LanguageAlpha2, nw.String()),
        (LanguageName, nw.String()),
        # mac address
        (MacAddress, nw.String()),
        # timezone
        (TimeZoneName, nw.String()),
    ],
)
def test_pydantic_extra_types(py_type_parser: PyTypeStep, input_type: Any, expected: nw.dtypes.DType) -> None:
    """Test that PyTypeStep handles pydantic-extra-types that inherit from str/float."""
    result = py_type_parser.parse(input_type, (), {})
    assert result == expected


def test_pydantic_extra_types_color(pydantic_parser: PydanticTypeStep) -> None:
    """Test that PydanticTypeStep handles Color (which doesn't inherit from str)."""
    result = pydantic_parser.parse(Color, (), {})
    assert result == nw.String()


def test_pydantic_extra_types_color_in_list(pydantic_parser: PydanticTypeStep) -> None:
    """Test that Color works in container types."""
    # Color in a list should work through the pipeline
    result = pydantic_parser.pipeline.parse(list[Color], (), {})
    assert result == nw.List(nw.String())
