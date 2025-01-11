from __future__ import annotations

from datetime import date
from datetime import datetime
from types import NoneType
from types import UnionType
from typing import TYPE_CHECKING
from typing import Any
from typing import GenericAlias
from typing import _GenericAlias

import narwhals as nw
from narwhals.schema import Schema

from anyschema._parsers._datetime import parse_datetime_metadata
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
    _type, _metadata = field_to_type_and_meta(field_info=field_info)

    if _type is int:
        return parse_integer_metadata(_metadata)

    if _type is float:
        # There is no way of differentiating between Float32 and Float64 in pydantic,
        # therefore no matter what the metadata are, we always return Float64
        return nw.Float64()

    if _type is bool:
        return nw.Boolean()

    if _type is str:
        return nw.String()

    if _type is date:
        return nw.Date()

    if _type is datetime:
        return parse_datetime_metadata(_metadata)

    raise NotImplementedError  # pragma: no cover


def field_to_type_and_meta(field_info: FieldInfo) -> tuple[type, tuple[Any]]:
    annotation = field_info.annotation
    if (is_union_type := isinstance(annotation, UnionType)) or isinstance(annotation, _GenericAlias | GenericAlias):
        if is_union_type and len(annotation.__args__) != 2:  # noqa: PLR2004
            msg = "Unsupported union with more than 2 types."
            raise NotImplementedError(msg)

        _field0, _field1 = annotation.__args__
        _field = _field1 if _field0 is NoneType else _field0
        _metadata = getattr(_field, "__metadata__", ())
        _type = getattr(_field, "__args__", (_field,))[0]

    else:
        _type = annotation
        _metadata = tuple(field_info.metadata)

    return _type, _metadata


__all__ = ("field_to_nw_type", "model_to_nw_schema")
