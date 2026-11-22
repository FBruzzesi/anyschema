from __future__ import annotations

import sys
from functools import cache
from typing import TYPE_CHECKING, NamedTuple

import narwhals as nw

from anyschema._dependencies import is_pydantic_base_model, is_pydantic_extra_types_color
from anyschema._metadata import get_anyschema_value_by_key
from anyschema.adapters import pydantic_adapter
from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep, parse_struct

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType

__all__ = ("PydanticTypeStep",)


class _PydanticTypes(NamedTuple):
    aware_datetime: type
    naive_datetime: type
    past_or_future_datetimes: tuple[type, ...]
    past_or_future_dates: tuple[type, ...]
    string_types: tuple[type, ...]
    secret_bytes: type


@cache
def _pydantic_types() -> _PydanticTypes:
    """Import the pydantic types on first parse, so building the pipeline does not import pydantic."""
    from pydantic import (
        AnyUrl,
        AwareDatetime,
        EmailStr,
        FutureDate,
        FutureDatetime,
        IPvAnyAddress,
        IPvAnyInterface,
        IPvAnyNetwork,
        MongoDsn,
        NaiveDatetime,
        NameEmail,
        PastDate,
        PastDatetime,
        PostgresDsn,
        SecretBytes,
        SecretStr,
        networks,
    )
    from pydantic_core import MultiHostUrl, Url

    # URL/DSN types: before pydantic 2.10 they are `Annotated[pydantic_core.Url | MultiHostUrl, ...]`, which
    # `AnnotatedStep` unwraps, so the `isinstance` filter drops the aliases. From 2.10 they are classes, and all but
    # the multi-host DSNs subclass `AnyUrl`. Only public names are used, so a pydantic refactor cannot silently break
    # this.
    string_types = tuple(
        tp
        for tp in (
            Url,
            MultiHostUrl,
            AnyUrl,
            PostgresDsn,
            MongoDsn,
            getattr(networks, "NatsDsn", None),  # pydantic>=2.6
            EmailStr,
            NameEmail,
            IPvAnyAddress,
            IPvAnyInterface,
            IPvAnyNetwork,
            SecretStr,
        )
        if isinstance(tp, type)
    )
    return _PydanticTypes(
        aware_datetime=AwareDatetime,  # pyright: ignore[reportArgumentType]  # pyrefly: ignore[bad-argument-type]
        naive_datetime=NaiveDatetime,  # pyright: ignore[reportArgumentType]  # pyrefly: ignore[bad-argument-type]
        past_or_future_datetimes=(PastDatetime, FutureDatetime),  # pyright: ignore[reportArgumentType]  # pyrefly: ignore[bad-argument-type]
        past_or_future_dates=(PastDate, FutureDate),  # pyright: ignore[reportArgumentType]  # pyrefly: ignore[bad-argument-type]
        string_types=string_types,
        secret_bytes=SecretBytes,
    )


class PydanticTypeStep(ParserStep):
    """Parser for Pydantic-specific types.

    Handles:

    - Pydantic datetime types (`AwareDatetime`, `NaiveDatetime`, etc.)
    - Pydantic date types (`PastDate`, `FutureDate`)
    - URLs, DSNs, `EmailStr`, `NameEmail`, `IPvAny*` and `SecretStr` as String
    - `SecretBytes` as Binary
    - `Color` from [pydantic-extra-types](https://github.com/pydantic/pydantic-extra-types) as String
    - Pydantic `BaseModel` (Struct types)

    Types defined as `Annotated[T, ...]` (e.g. `FilePath`, `UUID4`, `StrictStr`) are unwrapped by `AnnotatedStep`
    and parsed as `T`.

    Warning:
        It requires [pydantic](https://docs.pydantic.dev/latest/) to be installed.
    """

    def parse(  # noqa: C901
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
        # A pydantic type cannot reach the pipeline before the user imports pydantic. Generic aliases are not types.
        if "pydantic" not in sys.modules or not isinstance(input_type, type):
            return None

        pydantic_types = _pydantic_types()

        # Handle AwareDatetime
        if issubclass(input_type, pydantic_types.aware_datetime):
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

        if issubclass(input_type, pydantic_types.naive_datetime):
            # Pydantic NaiveDatetime should not receive a timezone.
            # If a timezone is specified via {"anyschema": {"time_zone": ...}}, we raise an error.
            if (time_zone := get_anyschema_value_by_key(metadata, key="time_zone")) is not None:
                msg = f"pydantic NaiveDatetime should not specify a timezone, found {time_zone}."
                raise UnsupportedDTypeError(msg)

            return nw.Datetime(
                time_unit=get_anyschema_value_by_key(metadata, key="time_unit", default="us"), time_zone=None
            )

        # Handle datetime types
        if issubclass(input_type, pydantic_types.past_or_future_datetimes):
            # PastDatetime and FutureDatetime accept both aware and naive datetimes.
            return nw.Datetime(
                time_unit=get_anyschema_value_by_key(metadata, key="time_unit", default="us"),
                time_zone=get_anyschema_value_by_key(metadata, key="time_zone"),
            )

        # Handle date types
        if issubclass(input_type, pydantic_types.past_or_future_dates):
            return nw.Date()

        # `Color` does not subclass `str`, so `PyTypeStep` would not catch it
        if issubclass(input_type, pydantic_types.string_types) or is_pydantic_extra_types_color(input_type):
            return nw.String()

        if issubclass(input_type, pydantic_types.secret_bytes):
            return nw.Binary()

        # Handle Pydantic models (Struct types)
        if is_pydantic_base_model(input_type):
            return parse_struct(self.pipeline, pydantic_adapter(input_type))

        # This parser doesn't handle this type
        return None
