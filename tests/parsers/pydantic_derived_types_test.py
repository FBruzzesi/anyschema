"""Tests for pydantic parser with derived types.

This module tests that PydanticTypeStep correctly handles types that inherit
from Pydantic's date/datetime types.
"""

from __future__ import annotations

from typing import Any

import narwhals as nw
import pytest
from pydantic import FutureDate, PastDate, PastDatetime

from anyschema.parsers import ParserPipeline, PyTypeStep, UnionTypeStep
from anyschema.parsers.pydantic import PydanticTypeStep


# Custom types that inherit from Pydantic types
class CustomPastDate(PastDate): ...


class CustomFutureDate(FutureDate): ...


class CustomPastDatetime(PastDatetime): ...


@pytest.fixture(scope="module")
def parser_pipeline() -> ParserPipeline:
    """Create a parser pipeline with pydantic support."""
    union_parser = UnionTypeStep()
    pydantic_parser = PydanticTypeStep()
    py_parser = PyTypeStep()
    chain = ParserPipeline([union_parser, pydantic_parser, py_parser])
    union_parser.pipeline = chain
    pydantic_parser.pipeline = chain
    py_parser.pipeline = chain
    return chain


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        # Base Pydantic types
        (PastDate, nw.Date()),
        (FutureDate, nw.Date()),
        (PastDatetime, nw.Datetime()),
        # Derived types
        (CustomPastDate, nw.Date()),
        (CustomFutureDate, nw.Date()),
        (CustomPastDatetime, nw.Datetime()),
        # In lists
        (list[CustomPastDate], nw.List(nw.Date())),
        (list[CustomPastDatetime], nw.List(nw.Datetime())),
    ],
)
def test_pydantic_derived_types(parser_pipeline: ParserPipeline, input_type: Any, expected: nw.dtypes.DType) -> None:
    """Test that pydantic parser handles derived types correctly."""
    result = parser_pipeline.parse(input_type, (), {})
    assert result == expected
