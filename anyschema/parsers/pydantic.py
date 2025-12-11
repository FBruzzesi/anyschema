from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw
from pydantic import AwareDatetime, BaseModel, FutureDate, FutureDatetime, NaiveDatetime, PastDate, PastDatetime

from anyschema._dependencies import is_pydantic_base_model
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
            constraints: Optional constraints associated with the type.
            metadata: Optional custom metadata dictionary.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        # Check if it's a type/class first (not a generic alias or other special form)
        if not isinstance(input_type, type):
            return None

        # Handle AwareDatetime
        if issubclass(input_type, AwareDatetime):  # pyright: ignore[reportArgumentType]
            # Pydantic AwareDatetime does not fix a single timezone, but any timezone would work.
            # This cannot be used in nw.Datetime, therefore we raise an exception
            # See https://github.com/pydantic/pydantic/issues/5829
            if (timezone := metadata.get("timezone")) is None:
                # TODO(FBruzzesi): Should we use another convention? A few possible options:
                #  * "time_zone"
                #  * "anyschema/timezone"
                #  * "anyschema/time_zone"
                msg = "pydantic AwareDatetime does not specify a fixed timezone."
                raise UnsupportedDTypeError(msg)

            return nw.Datetime(time_zone=timezone)

        # Handle datetime types
        if issubclass(input_type, (NaiveDatetime, PastDatetime, FutureDatetime)):  # pyright: ignore[reportArgumentType]
            # PastDatetime and FutureDatetime accept both aware and naive datetimes, here we
            # simply return nw.Datetime without timezone info.
            # This means that we won't be able to convert it to a timezone aware data type.
            return nw.Datetime()

        # Handle date types
        if issubclass(input_type, (PastDate, FutureDate)):  # pyright: ignore[reportArgumentType]
            return nw.Date()

        # Handle Pydantic models (Struct types)
        if is_pydantic_base_model(input_type):
            return self._parse_pydantic_model(input_type)

        # TODO(FBruzzesi): It's possible to map many more types, however we would lose the information that such type
        # would want to represent.
        # See https://docs.pydantic.dev/latest/api/types/ for more pydantic types and
        # https://docs.pydantic.dev/latest/api/pydantic_extra_types_* for pydantic extra types.

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
