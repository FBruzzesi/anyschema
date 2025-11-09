from __future__ import annotations

from datetime import date
from datetime import datetime
from types import UnionType
from typing import TYPE_CHECKING
from typing import Any
from typing import GenericAlias
from typing import Union
from typing import _GenericAlias
from typing import get_args
from typing import get_origin

import narwhals as nw
from narwhals.schema import Schema
from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import FutureDate
from pydantic import FutureDatetime
from pydantic import NaiveDatetime
from pydantic import PastDate
from pydantic import PastDatetime
from pydantic.fields import FieldInfo

from anyschema._annotated_types import has_integer_constraints
from anyschema._annotated_types import parse_integer_constraints
from anyschema._python_types import is_optional_type
from anyschema._python_types import parse_list_type
from anyschema._python_types import parse_python_type
from anyschema._python_types import unwrap_optional
from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from narwhals.dtypes import DType


def model_to_nw_schema(model: BaseModel | type[BaseModel]) -> Schema:
    """Convert a Pydantic model to a Narwhals Schema.
    
    Arguments:
        model: A Pydantic BaseModel class or instance.
        
    Returns:
        A Narwhals Schema representing the model's fields.
    """
    return Schema(
        {field_name: pydantic_field_to_nw_type(field_info) for field_name, field_info in model.model_fields.items()}
    )


def pydantic_field_to_nw_type(field_info: FieldInfo) -> DType:  # noqa: C901, PLR0911, PLR0912
    """Convert a Pydantic field to a Narwhals DType.
    
    This function handles Pydantic-specific types and delegates to generic parsers
    for common Python types.
    
    Arguments:
        field_info: Pydantic FieldInfo object containing the field's type and metadata.
        
    Returns:
        A Narwhals DType representing the field's type.
    """
    annotation = field_info.annotation

    # Handle generic types (list, Union, etc.)
    if isinstance(annotation, _GenericAlias | GenericAlias):
        _origin = get_origin(annotation)
        _args = get_args(annotation)

        if _origin is Union:
            # Handle Optional[T] / Union[T, None]
            if is_optional_type(annotation):
                _type, _metadata = unwrap_optional(annotation)
                return pydantic_field_to_nw_type(FieldInfo(annotation=_type, metadata=_metadata))
            else:
                msg = "Union with both types being not None is not supported."
                raise UnsupportedDTypeError(msg)

        elif _origin is list:
            # Handle list[T]
            list_result = parse_list_type(annotation)
            if list_result is not None:
                _inner_type, _inner_metadata = list_result
                return nw.List(inner=pydantic_field_to_nw_type(FieldInfo(annotation=_inner_type, metadata=_inner_metadata)))

        else:  # pragma: no cover
            msg = "Please report an issue at https://github.com/FBruzzesi/anyschema/issues"
            raise NotImplementedError(msg)

    # Handle UnionType (Python 3.10+ style Union with | operator)
    elif isinstance(annotation, UnionType):
        if is_optional_type(annotation):
            _type, _metadata = unwrap_optional(annotation)
            return pydantic_field_to_nw_type(FieldInfo(annotation=_type, metadata=_metadata))
        else:
            msg = "Union with both types being not None is not supported."
            raise UnsupportedDTypeError(msg)

    # Handle nested Pydantic models (Struct)
    elif (isinstance(annotation, type) and issubclass(annotation, BaseModel)) or isinstance(annotation, BaseModel):
        return nw.Struct(
            [
                nw.Field(name=_inner_field_name, dtype=pydantic_field_to_nw_type(_inner_field_info))
                for _inner_field_name, _inner_field_info in annotation.model_fields.items()
            ]
        )

    # For non-generic types, extract type and metadata
    else:
        _type = annotation
        _metadata = tuple(field_info.metadata)

    # Handle Pydantic-specific datetime types
    if _type is AwareDatetime:
        # Pydantic AwareDatetime does not fix a single timezone, but any timezone would work.
        # This cannot be used in nw.Datetime, therefore we raise an exception
        # See https://github.com/pydantic/pydantic/issues/5829
        msg = "pydantic AwareDatetime does not specify a fixed timezone."
        raise UnsupportedDTypeError(msg)

    if _type in {datetime, NaiveDatetime, PastDatetime, FutureDatetime}:
        # PastDatetime and FutureDatetime accept both aware and naive datetimes, here we
        # simply return nw.Datetime without timezone info.
        return nw.Datetime()

    if _type in {date, PastDate, FutureDate}:
        return nw.Date()

    # Handle integer with constraints (use annotated_types parser)
    if _type is int:
        if has_integer_constraints(_metadata):
            return parse_integer_constraints(_metadata)
        # Default to Int64 for plain int
        return nw.Int64()

    # Try parsing as basic Python type (float, str, bool, etc.)
    python_dtype = parse_python_type(_type, _metadata)
    if python_dtype is not None:
        return python_dtype

    # If we reach here, the type is not supported
    raise NotImplementedError  # pragma: no cover


__all__ = ("model_to_nw_schema", "pydantic_field_to_nw_type")
