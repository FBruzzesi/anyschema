from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import narwhals as nw
from pydantic import AwareDatetime, BaseModel, FutureDate, FutureDatetime, NaiveDatetime, PastDate, PastDatetime

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._base import TypeParser

if TYPE_CHECKING:
    from narwhals.dtypes import DType

__all__ = ("PydanticTypeParser",)


class PydanticTypeParser(TypeParser):
    """Parser for Pydantic-specific types.

    Handles:
    - Pydantic datetime types (AwareDatetime, NaiveDatetime, etc.)
    - Pydantic date types (PastDate, FutureDate)
    - Pydantic BaseModel (Struct types)
    """

    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:  # noqa: ARG002
        """Parse Pydantic-specific types into Narwhals dtypes.

        Arguments:
            input_type: The type to parse.
            metadata: Optional metadata associated with the type.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        # Handle AwareDatetime - this is unsupported
        if input_type is AwareDatetime:
            # Pydantic AwareDatetime does not fix a single timezone, but any timezone would work.
            # This cannot be used in nw.Datetime, therefore we raise an exception
            # See https://github.com/pydantic/pydantic/issues/5829
            msg = "pydantic AwareDatetime does not specify a fixed timezone."
            raise UnsupportedDTypeError(msg)

        # Handle datetime types
        if input_type in {datetime, NaiveDatetime, PastDatetime, FutureDatetime}:
            # PastDatetime and FutureDatetime accept both aware and naive datetimes, here we
            # simply return nw.Datetime without timezone info.
            # This means that we won't be able to convert it to a timezone aware data type.
            return nw.Datetime()

        # Handle date types
        if input_type in {date, PastDate, FutureDate}:
            return nw.Date()

        # Handle Pydantic models (Struct types)
        if isinstance(input_type, type) and issubclass(input_type, BaseModel):
            return self._parse_pydantic_model(input_type)

        # This parser doesn't handle this type
        return None

    def _parse_pydantic_model(self, model: type[BaseModel]) -> DType:
        """Parse a Pydantic model into a Struct type.

        Arguments:
            model: The Pydantic model class or instance.

        Returns:
            A Narwhals Struct dtype.
        """
        fields = []
        for field_name, field_info in model.model_fields.items():
            annotation, metadata = field_info.annotation, tuple(field_info.metadata)

            assert annotation is not None  # noqa: S101
            field_dtype = self.parser_chain.parse(annotation, metadata, strict=True)
            fields.append(nw.Field(name=field_name, dtype=field_dtype))

        return nw.Struct(fields)


__all__ = ("PydanticTypeParser",)
