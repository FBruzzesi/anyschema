from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import narwhals as nw
import pytest
from pydantic import (
    AwareDatetime,
    BaseModel,
    FutureDate,
    FutureDatetime,
    NaiveDatetime,
    PastDate,
    PastDatetime,
    SecretBytes,
    SecretStr,
)
from pydantic.networks import (
    AmqpDsn,
    AnyHttpUrl,
    AnyUrl,
    AnyWebsocketUrl,
    ClickHouseDsn,
    CockroachDsn,
    EmailStr,
    FileUrl,
    FtpUrl,
    HttpUrl,
    IPvAnyAddress,
    IPvAnyInterface,
    IPvAnyNetwork,
    KafkaDsn,
    MariaDBDsn,
    MongoDsn,
    MySQLDsn,
    NameEmail,
    NatsDsn,
    PostgresDsn,
    RedisDsn,
    SnowflakeDsn,
    WebsocketUrl,
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


# --- Tests for new pydantic.types ---


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        # Secret types
        (SecretStr, nw.String()),
        (SecretBytes, nw.Binary()),
        # Path types
        (Path, nw.String()),
        # UUID types
        (UUID, nw.String()),
    ],
)
def test_parse_pydantic_types_new(
    pydantic_parser: PydanticTypeStep, input_type: type, expected: nw.dtypes.DType
) -> None:
    """Test parsing of new pydantic types (secrets, paths, UUIDs)."""
    result = pydantic_parser.parse(input_type, constraints=(), metadata={})
    assert result == expected


# --- Tests for pydantic.networks ---


@pytest.mark.parametrize(
    "input_type",
    [
        # URL types
        AnyUrl,
        AnyHttpUrl,
        HttpUrl,
        AnyWebsocketUrl,
        WebsocketUrl,
        FileUrl,
        FtpUrl,
        # DSN types
        PostgresDsn,
        CockroachDsn,
        MySQLDsn,
        MariaDBDsn,
        RedisDsn,
        MongoDsn,
        KafkaDsn,
        NatsDsn,
        AmqpDsn,
        ClickHouseDsn,
        SnowflakeDsn,
        # Email types
        EmailStr,
        NameEmail,
        # IP types
        IPvAnyAddress,
        IPvAnyInterface,
        IPvAnyNetwork,
    ],
)
def test_parse_pydantic_network_types(pydantic_parser: PydanticTypeStep, input_type: type) -> None:
    """Test parsing of pydantic network types (URLs, DSNs, emails, IPs)."""
    result = pydantic_parser.parse(input_type, constraints=(), metadata={})
    assert result == nw.String()


# --- Tests for models with new types ---


def test_parse_model_with_network_types(pydantic_parser: PydanticTypeStep) -> None:
    """Test parsing a model that uses network types."""

    class ServerConfig(BaseModel):
        database_url: PostgresDsn
        cache_url: RedisDsn
        homepage: HttpUrl

    result = pydantic_parser.parse(ServerConfig, constraints=(), metadata={})

    expected_fields = [
        nw.Field(name="database_url", dtype=nw.String()),
        nw.Field(name="cache_url", dtype=nw.String()),
        nw.Field(name="homepage", dtype=nw.String()),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_model_with_secret_types(pydantic_parser: PydanticTypeStep) -> None:
    """Test parsing a model that uses secret types."""

    class Credentials(BaseModel):
        username: str
        password: SecretStr
        api_key: SecretBytes

    result = pydantic_parser.parse(Credentials, constraints=(), metadata={})

    expected_fields = [
        nw.Field(name="username", dtype=nw.String()),
        nw.Field(name="password", dtype=nw.String()),
        nw.Field(name="api_key", dtype=nw.Binary()),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected


def test_parse_model_with_url_types(pydantic_parser: PydanticTypeStep) -> None:
    """Test parsing a model that uses URL types."""

    class Website(BaseModel):
        homepage: HttpUrl
        websocket_endpoint: WebsocketUrl
        file_location: FileUrl

    result = pydantic_parser.parse(Website, constraints=(), metadata={})

    expected_fields = [
        nw.Field(name="homepage", dtype=nw.String()),
        nw.Field(name="websocket_endpoint", dtype=nw.String()),
        nw.Field(name="file_location", dtype=nw.String()),
    ]
    expected = nw.Struct(expected_fields)
    assert result == expected
