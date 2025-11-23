from __future__ import annotations

from datetime import date, datetime
from typing import Any

import narwhals as nw
import pytest
from pydantic import AwareDatetime, BaseModel, FutureDate, FutureDatetime, NaiveDatetime, PastDate, PastDatetime

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers import ParserPipeline
from anyschema.parsers._builtin import PyTypeStep
from anyschema.parsers.pydantic import PydanticTypeStep


@pytest.fixture(scope="module")
def pydantic_parser() -> PydanticTypeStep:
    """Create a PydanticTypeStep instance with pipeline set."""
    parser = PydanticTypeStep()
    py_parser = PyTypeStep()
    chain = ParserPipeline([parser, py_parser])
    parser.pipeline = chain
    py_parser.pipeline = chain
    return parser


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (NaiveDatetime, nw.Datetime()),
        (PastDatetime, nw.Datetime()),
        (FutureDatetime, nw.Datetime()),
        (PastDate, nw.Date()),
        (FutureDate, nw.Date()),
    ],
)
def test_parse_pydantic_types(pydantic_parser: PydanticTypeStep, input_type: type, expected: nw.dtypes.DType) -> None:
    result = pydantic_parser.parse(input_type)
    assert result == expected


def test_parse_aware_datetime_raises(pydantic_parser: PydanticTypeStep) -> None:
    expected_msg = "pydantic AwareDatetime does not specify a fixed timezone."
    with pytest.raises(UnsupportedDTypeError, match=expected_msg):
        pydantic_parser.parse(AwareDatetime)


def test_parse_model_into_struct(pydantic_parser: PydanticTypeStep) -> None:
    class SomeModel(BaseModel):
        past_date: PastDate
        future_date: FutureDate
        updated_at: NaiveDatetime

    result = pydantic_parser.parse(SomeModel)

    expected_fields = [
        nw.Field(name="past_date", dtype=nw.Date()),
        nw.Field(name="future_date", dtype=nw.Date()),
        nw.Field(name="updated_at", dtype=nw.Datetime()),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_nested_model(pydantic_parser: PydanticTypeStep) -> None:
    class Address(BaseModel):
        street: str
        city: str

    class Person(BaseModel):
        name: str
        address: Address

    result = pydantic_parser.parse(Person)

    address_fields = [
        nw.Field(name="street", dtype=nw.String()),
        nw.Field(name="city", dtype=nw.String()),
    ]
    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="address", dtype=nw.Struct(address_fields)),
    ]
    expected = nw.Struct(expected_fields)

    assert result == expected


def test_parse_empty_model(pydantic_parser: PydanticTypeStep) -> None:
    """Test parsing an empty Pydantic model."""

    class EmptyModel(BaseModel):
        pass

    result = pydantic_parser.parse(EmptyModel)

    expected = nw.Struct([])
    assert result == expected


@pytest.mark.parametrize("input_type", [int, float, list[int], date, datetime])
def parse_non_pydantic_types(pydantic_parser: PydanticTypeStep, input_type: Any) -> None:
    result = pydantic_parser.parse(input_type)
    assert result is None


def test_parse_custom_class_returns_none(pydantic_parser: PydanticTypeStep) -> None:
    """Test that parsing non-BaseModel class returns None."""

    class CustomClass:
        pass

    result = pydantic_parser.parse(CustomClass)
    assert result is None


def test_parse_model_with_field_metadata(pydantic_parser: PydanticTypeStep) -> None:
    """Test parsing model that has field metadata."""
    from typing import Annotated

    from pydantic import Field

    class ModelWithMetadata(BaseModel):
        name: Annotated[str, Field(min_length=1, max_length=100)]
        age: Annotated[int, Field(gt=0, lt=150)]

    result = pydantic_parser.parse(ModelWithMetadata)

    # The metadata is stored in field_info.metadata but the parsing should still work
    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="age", dtype=nw.Int64()),
    ]
    expected = nw.Struct(expected_fields)

    assert result == expected
