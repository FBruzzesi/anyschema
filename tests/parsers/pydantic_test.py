from __future__ import annotations

from datetime import date, datetime
from typing import Any

import narwhals as nw
import pydantic
import pytest
from pydantic import (
    AwareDatetime,
    BaseModel,
    DirectoryPath,
    FilePath,
    FutureDate,
    FutureDatetime,
    HttpUrl,
    NaiveDatetime,
    PastDate,
    PastDatetime,
    PostgresDsn,
    SecretBytes,
    SecretStr,
    networks,
)

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers import ParserPipeline
from anyschema.parsers._builtin import PyTypeStep
from anyschema.parsers.pydantic import PydanticTypeStep


@pytest.fixture(scope="module")
def pydantic_parser() -> PydanticTypeStep:
    """Create a PydanticTypeStep instance with pipeline set."""
    parser = PydanticTypeStep()
    py_parser = PyTypeStep()
    _ = ParserPipeline([parser, py_parser])
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
    result = pydantic_parser.parse(input_type, constraints=(), metadata={})
    assert result == expected


@pytest.mark.parametrize(
    ("input_type", "metadata", "expected"),
    [
        (NaiveDatetime, {"anyschema": {"time_unit": "ms"}}, nw.Datetime("ms")),
        (NaiveDatetime, {"anyschema": {"time_unit": "ns"}}, nw.Datetime("ns")),
        (PastDatetime, {"anyschema": {"time_unit": "ms"}}, nw.Datetime("ms")),
        (PastDatetime, {"anyschema": {"time_zone": "UTC"}}, nw.Datetime("us", time_zone="UTC")),
        (
            PastDatetime,
            {"anyschema": {"time_unit": "ms", "time_zone": "UTC"}},
            nw.Datetime("ms", time_zone="UTC"),
        ),
        (FutureDatetime, {"anyschema": {"time_unit": "ns"}}, nw.Datetime("ns")),
        (FutureDatetime, {"anyschema": {"time_zone": "Europe/Rome"}}, nw.Datetime("us", time_zone="Europe/Rome")),
        (
            FutureDatetime,
            {"anyschema": {"time_unit": "ns", "time_zone": "America/Los_Angeles"}},
            nw.Datetime("ns", time_zone="America/Los_Angeles"),
        ),
    ],
)
def test_parse_pydantic_datetime_with_metadata(
    pydantic_parser: PydanticTypeStep,
    input_type: type,
    metadata: dict[str, Any],
    expected: nw.dtypes.DType,
) -> None:
    """Test that pydantic datetime types parse correctly with anyschema/time_zone and anyschema/time_unit metadata."""
    result = pydantic_parser.parse(input_type, constraints=(), metadata=metadata)
    assert result == expected


def test_parse_aware_datetime_raises(pydantic_parser: PydanticTypeStep) -> None:
    expected_msg = "pydantic AwareDatetime does not specify a fixed timezone."
    with pytest.raises(UnsupportedDTypeError, match=expected_msg):
        pydantic_parser.parse(AwareDatetime, constraints=(), metadata={})


def test_parse_aware_datetime_with_tz(pydantic_parser: PydanticTypeStep) -> None:
    result = pydantic_parser.parse(
        AwareDatetime, constraints=(), metadata={"anyschema": {"time_zone": "Europe/Berlin"}}
    )
    assert result == nw.Datetime(time_zone="Europe/Berlin")


def test_parse_aware_datetime_with_tz_and_time_unit(pydantic_parser: PydanticTypeStep) -> None:
    result = pydantic_parser.parse(
        AwareDatetime,
        constraints=(),
        metadata={"anyschema": {"time_zone": "Europe/Berlin", "time_unit": "ms"}},
    )
    assert result == nw.Datetime(time_unit="ms", time_zone="Europe/Berlin")


def test_parse_model_into_struct(pydantic_parser: PydanticTypeStep) -> None:
    class SomeModel(BaseModel):
        past_date: PastDate
        future_date: FutureDate
        updated_at: NaiveDatetime

    result = pydantic_parser.parse(SomeModel, constraints=(), metadata={})

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

    result = pydantic_parser.parse(Person, constraints=(), metadata={})

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

    result = pydantic_parser.parse(EmptyModel, constraints=(), metadata={})

    expected = nw.Struct([])
    assert result == expected


@pytest.mark.parametrize("input_type", [int, float, list[int], date, datetime])
def test_parse_non_pydantic_types(pydantic_parser: PydanticTypeStep, input_type: Any) -> None:
    result = pydantic_parser.parse(input_type, constraints=(), metadata={})
    assert result is None


def test_parse_custom_class_returns_none(pydantic_parser: PydanticTypeStep) -> None:
    """Test that parsing non-BaseModel class returns None."""

    class CustomClass:
        pass

    result = pydantic_parser.parse(CustomClass, constraints=(), metadata={})
    assert result is None


def test_parse_model_with_field_metadata(pydantic_parser: PydanticTypeStep) -> None:
    """Test parsing model that has field metadata."""
    from typing import Annotated

    from pydantic import Field

    class ModelWithConstraints(BaseModel):
        name: Annotated[str, Field(min_length=1, max_length=100)]
        age: Annotated[int, Field(gt=0, lt=150)]

    result = pydantic_parser.parse(ModelWithConstraints, constraints=(), metadata={})

    # The metadata is stored in field_info.metadata but the parsing should still work
    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="age", dtype=nw.Int64()),
    ]
    expected = nw.Struct(expected_fields)

    assert result == expected


def test_parse_naive_datetime_with_timezone_raises(pydantic_parser: PydanticTypeStep) -> None:
    """Test that NaiveDatetime with timezone raises an error."""
    expected_msg = "pydantic NaiveDatetime should not specify a timezone, found UTC."
    with pytest.raises(UnsupportedDTypeError, match=expected_msg):
        pydantic_parser.parse(NaiveDatetime, constraints=(), metadata={"anyschema": {"time_zone": "UTC"}})


# URL/DSN names differ across pydantic versions, discover them so new ones are covered too.
_NETWORK_TYPE_NAMES = sorted(
    {name for name in networks.__all__ if name.endswith(("Url", "Dsn"))}
    | {"EmailStr", "NameEmail", "IPvAnyAddress", "IPvAnyInterface", "IPvAnyNetwork"}
)


@pytest.mark.parametrize("name", _NETWORK_TYPE_NAMES)
def test_parse_pydantic_network_types(auto_pipeline: ParserPipeline, name: str) -> None:
    # Goes through the full pipeline: in pydantic<2.10 URL types are `Annotated[pydantic_core.Url, ...]`
    result = auto_pipeline.parse(getattr(pydantic, name), constraints=(), metadata={})
    assert result == nw.String()


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (SecretStr, nw.String()),
        (SecretBytes, nw.Binary()),
        (FilePath, nw.String()),
        (DirectoryPath, nw.String()),
        (pydantic.UUID4, nw.String()),
    ],
)
def test_parse_pydantic_secret_and_annotated_types(
    auto_pipeline: ParserPipeline, input_type: Any, expected: nw.dtypes.DType
) -> None:
    result = auto_pipeline.parse(input_type, constraints=(), metadata={})
    assert result == expected


def test_parse_model_with_pydantic_types(auto_pipeline: ParserPipeline) -> None:
    class Config(BaseModel):
        homepage: HttpUrl
        database_url: PostgresDsn
        password: SecretStr
        api_key: SecretBytes
        config_file: FilePath
        tags: list[HttpUrl]

    result = auto_pipeline.parse(Config, constraints=(), metadata={})

    expected = nw.Struct(
        [
            nw.Field(name="homepage", dtype=nw.String()),
            nw.Field(name="database_url", dtype=nw.String()),
            nw.Field(name="password", dtype=nw.String()),
            nw.Field(name="api_key", dtype=nw.Binary()),
            nw.Field(name="config_file", dtype=nw.String()),
            nw.Field(name="tags", dtype=nw.List(nw.String())),
        ]
    )
    assert result == expected
