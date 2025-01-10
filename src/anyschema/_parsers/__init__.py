from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw
from narwhals.schema import Schema

from anyschema._parsers._integer import parse_integer_metadata

if TYPE_CHECKING:
    from narwhals.dtypes import DType
    from pydantic import BaseModel
    from pydantic.fields import FieldInfo


def model_to_nw_schema(model: BaseModel) -> Schema:
    """Converts Pydantic model to Narwhals Schema."""
    return Schema({field_name: field_to_nw_type(field_info) for field_name, field_info in model.model_fields.items()})


def field_to_nw_type(field_info: FieldInfo) -> DType:
    """Parse Pydantic FieldInfo into Narwhals dtype."""
    _type, _metadata = field_info.annotation, field_info.metadata
    if _type is int:
        return parse_integer_metadata(_metadata)
    if _type is float:  # There is no way of differentiating between Float32 and Float64 in pydantic
        return nw.Float64()
    raise NotImplementedError


__all__ = ("field_to_nw_type", "model_to_nw_schema")
