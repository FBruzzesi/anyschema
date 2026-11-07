from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw

from anyschema.parsers._base import ParserStep
from anyschema._dependencies import is_dataclass

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import AttrsClassType, FieldConstraints, FieldMetadata, FieldType


__all__ = ("DataclassTypeStep",)


class DataclassTypeStep(ParserStep):
    """Parser for Dataclasses types.

    Handles:

    - dataclasses.dataclass decorated classes

    """

    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,  # noqa: ARG002
        metadata: FieldMetadata,
    ) -> DType | None:
        if is_dataclass(input_type):
            return self.__parse_dataclass(input_type)

        # This parser doesn't handle this type
        return None

    def __parse_dataclass(self, dc_dataclass: type[DataclassType]) -> DType:
        """Parse a Pydantic model into a Struct type.

        Arguments:
            dc_dataclass: The dataclass type or instance.

        Returns:
            A Narwhals Struct dtype.
        """
        from anyschema.adapters import dataclass_adapter

        return nw.Struct(
            [
                nw.Field(
                    name=field_name,
                    dtype=self.pipeline.parse(field_info, field_constraints, field_metadata, strict=True),
                )
                for field_name, field_info, field_constraints, field_metadata in dataclass_adapter(dc_dataclass)
            ]
        )
