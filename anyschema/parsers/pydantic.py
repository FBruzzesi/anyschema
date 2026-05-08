from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import narwhals as nw
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
    AnyUrl,
    EmailStr,
    IPvAnyAddress,
    IPvAnyInterface,
    IPvAnyNetwork,
    NameEmail,
    _BaseMultiHostUrl,
)

# Note: Most pydantic.networks URL/DSN types inherit from AnyUrl or _BaseMultiHostUrl:
# - AnyUrl subclasses: AnyHttpUrl, HttpUrl, AnyWebsocketUrl, WebsocketUrl, FileUrl, FtpUrl,
#   CockroachDsn, MySQLDsn, MariaDBDsn, RedisDsn, KafkaDsn, AmqpDsn, ClickHouseDsn, SnowflakeDsn
# - _BaseMultiHostUrl subclasses: PostgresDsn, MongoDsn, NatsDsn
from anyschema._dependencies import is_pydantic_base_model
from anyschema._metadata import get_anyschema_value_by_key
from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType

__all__ = ("PydanticTypeStep",)

_INTO_STRING_TYPES: tuple[Any, ...] = (
    # IP Types
    IPvAnyAddress,
    IPvAnyInterface,
    IPvAnyNetwork,
    SecretStr,
    Path,  # FilePath, DirectoryPath, NewPath all inherit from Path
    UUID,  # UUID1-UUID8 are Annotated[UUID, ...]
    AnyUrl,  # All URL/DSN types inherit from AnyUrl (except multi-host DSNs)
    _BaseMultiHostUrl,  # PostgresDsn, MongoDsn, NatsDsn inherit from this
    EmailStr,
    NameEmail,
)


def _get_pydantic_extra_types_color() -> type | None:
    """Get pydantic_extra_types.color.Color if available."""
    if (color_module := sys.modules.get("pydantic_extra_types.color")) is not None:
        return getattr(color_module, "Color", None)
    return None


class PydanticTypeStep(ParserStep):
    """Parser for Pydantic-specific types.

    Handles:

    - Pydantic datetime types (`AwareDatetime`, `NaiveDatetime`, etc.)
    - Pydantic date types (`PastDate`, `FutureDate`)
    - Pydantic secret types (`SecretStr`, `SecretBytes`)
    - Pydantic path types (`FilePath`, `DirectoryPath`, `NewPath`)
    - Pydantic network types (URLs, DSNs, Email, IP addresses)
    - Pydantic extra types (`Color` from pydantic-extra-types)
    - Pydantic `BaseModel` (Struct types)

    Warning:
        It requires [pydantic](https://docs.pydantic.dev/latest/) to be installed.
    """

    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,  # noqa: ARG002
        metadata: FieldMetadata,
    ) -> DType | None:
        """Parse Pydantic-specific types into Narwhals dtypes.

        Arguments:
            input_type: The type to parse.
            constraints: Constraints associated with the type.
            metadata: Custom metadata dictionary.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        # Check if it's a type/class first (not a generic alias or other special form)
        if not isinstance(input_type, type):
            return None

        if result := self._parse_datetime_types(input_type, metadata):
            return result

        if issubclass(input_type, (PastDate, FutureDate)):  # pyright: ignore[reportArgumentType]
            return nw.Date()

        if issubclass(input_type, SecretBytes):
            return nw.Binary()

        if issubclass(input_type, _INTO_STRING_TYPES):
            return nw.String()

        # Handle pydantic-extra-types Color (doesn't inherit from str)
        if (color_cls := _get_pydantic_extra_types_color()) is not None and issubclass(input_type, color_cls):
            return nw.String()

        if is_pydantic_base_model(input_type):
            return self._parse_pydantic_model(input_type)

        return None

    def _parse_datetime_types(self, input_type: type, metadata: FieldMetadata) -> DType | None:
        """Parse Pydantic datetime types.

        Arguments:
            input_type: The type to parse.
            metadata: Custom metadata dictionary.

        Returns:
            A Narwhals Datetime DType if this is a datetime type, None otherwise.
        """
        if issubclass(input_type, AwareDatetime):  # pyright: ignore[reportArgumentType]  # ty: ignore[invalid-argument-type]
            # Pydantic AwareDatetime does not fix a single timezone, but any timezone would work.
            # See https://github.com/pydantic/pydantic/issues/5829
            # Unless a timezone is specified via {"anyschema": {"time_zone": ...}}, we raise an error.
            if (time_zone := get_anyschema_value_by_key(metadata, key="time_zone")) is None:
                msg = (
                    "pydantic AwareDatetime does not specify a fixed timezone.\n\n"
                    "Hint: You can specify a timezone via "
                    "`Field(..., json_schema_extra={'anyschema': {'time_zone': 'UTC'}})`"
                )
                raise UnsupportedDTypeError(msg)

            return nw.Datetime(
                time_unit=get_anyschema_value_by_key(metadata, key="time_unit", default="us"), time_zone=time_zone
            )

        if issubclass(input_type, NaiveDatetime):  # pyright: ignore[reportArgumentType] # ty: ignore[invalid-argument-type]
            # Pydantic NaiveDatetime should not receive a timezone.
            # If a timezone is specified via {"anyschema": {"time_zone": ...}}, we raise an error.
            if (time_zone := get_anyschema_value_by_key(metadata, key="time_zone")) is not None:
                msg = f"pydantic NaiveDatetime should not specify a timezone, found {time_zone}."
                raise UnsupportedDTypeError(msg)

            return nw.Datetime(
                time_unit=get_anyschema_value_by_key(metadata, key="time_unit", default="us"), time_zone=None
            )

        if issubclass(input_type, (PastDatetime, FutureDatetime)):  # pyright: ignore[reportArgumentType]
            # PastDatetime and FutureDatetime accept both aware and naive datetimes.
            return nw.Datetime(
                time_unit=get_anyschema_value_by_key(metadata, key="time_unit", default="us"),
                time_zone=get_anyschema_value_by_key(metadata, key="time_zone"),
            )

        return None

    def _parse_pydantic_model(self, model: type[BaseModel]) -> DType:
        """Parse a Pydantic model into a Struct type.

        Arguments:
            model: The Pydantic model class or instance.

        Returns:
            A Narwhals Struct dtype.
        """
        from anyschema.adapters import pydantic_adapter

        return nw.Struct(
            [
                nw.Field(
                    name=field_name,
                    dtype=self.pipeline.parse(field_info, field_constraints, field_metadata, strict=True),
                )
                for field_name, field_info, field_constraints, field_metadata in pydantic_adapter(model)
            ]
        )
