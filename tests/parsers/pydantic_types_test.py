from __future__ import annotations

from datetime import date, datetime

import narwhals as nw
import pytest
from pydantic import AwareDatetime, BaseModel, FutureDate, FutureDatetime, NaiveDatetime, PastDate, PastDatetime

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserChain
from anyschema.parsers._builtin import PyTypeParser
from anyschema.parsers.pydantic import PydanticTypeParser


@pytest.fixture
def parser() -> PydanticTypeParser:
    """Create a PydanticTypeParser instance with parser_chain set."""
    parser = PydanticTypeParser()
    py_parser = PyTypeParser()
    chain = ParserChain([parser, py_parser])
    parser.parser_chain = chain
    py_parser.parser_chain = chain
    return parser


def test_parse_datetime(parser: PydanticTypeParser) -> None:
    """Test parsing datetime type."""
    result = parser.parse(datetime)
    assert result == nw.Datetime()


def test_parse_naive_datetime(parser: PydanticTypeParser) -> None:
    """Test parsing NaiveDatetime type."""
    result = parser.parse(NaiveDatetime)
    assert result == nw.Datetime()


def test_parse_past_datetime(parser: PydanticTypeParser) -> None:
    """Test parsing PastDatetime type."""
    result = parser.parse(PastDatetime)
    assert result == nw.Datetime()


def test_parse_future_datetime(parser: PydanticTypeParser) -> None:
    """Test parsing FutureDatetime type."""
    result = parser.parse(FutureDatetime)
    assert result == nw.Datetime()


def test_parse_aware_datetime_raises(parser: PydanticTypeParser) -> None:
    """Test parsing AwareDatetime raises UnsupportedDTypeError."""
    expected_msg = "pydantic AwareDatetime does not specify a fixed timezone."
    with pytest.raises(UnsupportedDTypeError, match=expected_msg):
        parser.parse(AwareDatetime)


def test_parse_date(parser: PydanticTypeParser) -> None:
    """Test parsing date type."""
    result = parser.parse(date)
    assert result == nw.Date()


def test_parse_past_date(parser: PydanticTypeParser) -> None:
    """Test parsing PastDate type."""
    result = parser.parse(PastDate)
    assert result == nw.Date()


def test_parse_future_date(parser: PydanticTypeParser) -> None:
    """Test parsing FutureDate type."""
    result = parser.parse(FutureDate)
    assert result == nw.Date()


def test_parse_simple_model(parser: PydanticTypeParser) -> None:
    """Test parsing a simple Pydantic model."""

    class SimpleModel(BaseModel):
        name: str
        age: int

    result = parser.parse(SimpleModel)

    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="age", dtype=nw.Int64()),
    ]
    expected = nw.Struct(expected_fields)

    assert result == expected


def test_parse_model_with_multiple_fields(parser: PydanticTypeParser) -> None:
    """Test parsing a model with various field types."""

    class ComplexModel(BaseModel):
        name: str
        age: int
        score: float
        active: bool

    result = parser.parse(ComplexModel)

    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="age", dtype=nw.Int64()),
        nw.Field(name="score", dtype=nw.Float64()),
        nw.Field(name="active", dtype=nw.Boolean()),
    ]
    expected = nw.Struct(expected_fields)

    assert result == expected


def test_parse_model_with_date_fields(parser: PydanticTypeParser) -> None:
    """Test parsing a model with date fields."""

    class DateModel(BaseModel):
        birth_date: date
        past_date: PastDate
        future_date: FutureDate

    result = parser.parse(DateModel)

    expected_fields = [
        nw.Field(name="birth_date", dtype=nw.Date()),
        nw.Field(name="past_date", dtype=nw.Date()),
        nw.Field(name="future_date", dtype=nw.Date()),
    ]
    expected = nw.Struct(expected_fields)

    assert result == expected


def test_parse_model_with_datetime_fields(parser: PydanticTypeParser) -> None:
    """Test parsing a model with datetime fields."""

    class DateTimeModel(BaseModel):
        created_at: datetime
        updated_at: NaiveDatetime

    result = parser.parse(DateTimeModel)

    expected_fields = [
        nw.Field(name="created_at", dtype=nw.Datetime()),
        nw.Field(name="updated_at", dtype=nw.Datetime()),
    ]
    expected = nw.Struct(expected_fields)

    assert result == expected


def test_parse_nested_model(parser: PydanticTypeParser) -> None:
    """Test parsing a model with nested BaseModel fields."""

    class Address(BaseModel):
        street: str
        city: str

    class Person(BaseModel):
        name: str
        address: Address

    result = parser.parse(Person)

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


def test_parse_model_with_list_fields(parser: PydanticTypeParser) -> None:
    """Test parsing a model with list fields."""

    class ListModel(BaseModel):
        names: list[str]
        scores: list[int]

    result = parser.parse(ListModel)

    expected_fields = [
        nw.Field(name="names", dtype=nw.List(nw.String())),
        nw.Field(name="scores", dtype=nw.List(nw.Int64())),
    ]
    expected = nw.Struct(expected_fields)

    assert result == expected


def test_parse_model_class_vs_instance(parser: PydanticTypeParser) -> None:
    """Test parsing a Pydantic model class (not instance)."""

    class SimpleModel(BaseModel):
        name: str
        age: int

    # Parse the class, not the instance
    result = parser.parse(SimpleModel)

    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="age", dtype=nw.Int64()),
    ]
    expected = nw.Struct(expected_fields)

    assert result == expected


def test_parse_empty_model(parser: PydanticTypeParser) -> None:
    """Test parsing an empty Pydantic model."""

    class EmptyModel(BaseModel):
        pass

    result = parser.parse(EmptyModel)

    expected = nw.Struct([])
    assert result == expected


def test_parse_int_returns_none(parser: PydanticTypeParser) -> None:
    """Test that parsing int returns None (handled by PyTypeParser)."""
    result = parser.parse(int)
    assert result is None


def test_parse_str_returns_none(parser: PydanticTypeParser) -> None:
    """Test that parsing str returns None (handled by PyTypeParser)."""
    result = parser.parse(str)
    assert result is None


def test_parse_float_returns_none(parser: PydanticTypeParser) -> None:
    """Test that parsing float returns None (handled by PyTypeParser)."""
    result = parser.parse(float)
    assert result is None


def test_parse_custom_class_returns_none(parser: PydanticTypeParser) -> None:
    """Test that parsing non-BaseModel class returns None."""

    class CustomClass:
        pass

    result = parser.parse(CustomClass)
    assert result is None


def test_parse_datetime_with_metadata(parser: PydanticTypeParser) -> None:
    """Test parsing datetime with metadata (metadata is ignored)."""
    result = parser.parse(datetime, metadata=("some", "metadata"))
    assert result == nw.Datetime()


def test_parse_model_with_field_metadata(parser: PydanticTypeParser) -> None:
    """Test parsing model that has field metadata."""
    from typing import Annotated

    from pydantic import Field

    class ModelWithMetadata(BaseModel):
        name: Annotated[str, Field(min_length=1, max_length=100)]
        age: Annotated[int, Field(gt=0, lt=150)]

    result = parser.parse(ModelWithMetadata)

    # The metadata is stored in field_info.metadata but the parsing should still work
    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="age", dtype=nw.Int64()),
    ]
    expected = nw.Struct(expected_fields)

    assert result == expected


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (datetime, nw.Datetime()),
        (NaiveDatetime, nw.Datetime()),
        (PastDatetime, nw.Datetime()),
        (FutureDatetime, nw.Datetime()),
        (date, nw.Date()),
        (PastDate, nw.Date()),
        (FutureDate, nw.Date()),
    ],
)
def test_parse_datetime_date_types_parametrized(input_type: type, expected: nw.DType) -> None:
    """Parametrized test for Pydantic datetime and date types."""
    parser = PydanticTypeParser()
    py_parser = PyTypeParser()
    chain = ParserChain([parser, py_parser])
    parser.parser_chain = chain
    py_parser.parser_chain = chain

    result = parser.parse(input_type)
    assert result == expected
