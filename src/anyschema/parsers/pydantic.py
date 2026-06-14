from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw
from pydantic import AwareDatetime, BaseModel, FutureDate, FutureDatetime, NaiveDatetime, PastDate, PastDatetime

from anyschema._dependencies import is_pydantic_base_model
from anyschema._metadata import get_anyschema_value_by_key
from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType

__all__ = ("PydanticTypeStep",)


class PydanticTypeStep(ParserStep):
    """Parser for Pydantic-specific types.

    Handles:

    - Pydantic datetime types (`AwareDatetime`, `NaiveDatetime`, etc.)
    - Pydantic date types (`PastDate`, `FutureDate`)
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

        # Handle AwareDatetime
        if issubclass(input_type, AwareDatetime):  # pyright: ignore[reportArgumentType]
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

        if issubclass(input_type, NaiveDatetime):  # pyright: ignore[reportArgumentType]
            # Pydantic NaiveDatetime should not receive a timezone.
            # If a timezone is specified via {"anyschema": {"time_zone": ...}}, we raise an error.
            if (time_zone := get_anyschema_value_by_key(metadata, key="time_zone")) is not None:
                msg = f"pydantic NaiveDatetime should not specify a timezone, found {time_zone}."
                raise UnsupportedDTypeError(msg)

            return nw.Datetime(
                time_unit=get_anyschema_value_by_key(metadata, key="time_unit", default="us"), time_zone=None
            )

        # Handle datetime types
        if issubclass(input_type, (PastDatetime, FutureDatetime)):  # pyright: ignore[reportArgumentType]
            # PastDatetime and FutureDatetime accept both aware and naive datetimes.
            return nw.Datetime(
                time_unit=get_anyschema_value_by_key(metadata, key="time_unit", default="us"),
                time_zone=get_anyschema_value_by_key(metadata, key="time_zone"),
            )

        # Handle date types
        if issubclass(input_type, (PastDate, FutureDate)):  # pyright: ignore[reportArgumentType]
            return nw.Date()

        # Handle Pydantic models (Struct types)
        if is_pydantic_base_model(input_type):
            return self._parse_pydantic_model(input_type)

        # TODO(FBruzzesi): Add support for more pydantic types. See https://github.com/FBruzzesi/anyschema/issues/45

        # This parser doesn't handle this type
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
