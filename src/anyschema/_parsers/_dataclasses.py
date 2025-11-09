from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING
from typing import Any
from typing import get_type_hints

import narwhals as nw
from narwhals.schema import Schema

from anyschema._annotated_types import has_integer_constraints
from anyschema._annotated_types import parse_integer_constraints
from anyschema._python_types import is_optional_type
from anyschema._python_types import parse_list_type
from anyschema._python_types import parse_python_type
from anyschema._python_types import unwrap_optional

if TYPE_CHECKING:
    from narwhals.dtypes import DType


def dataclass_to_nw_schema(dataclass_type: type[Any]) -> Schema:
    """Convert a dataclass to a Narwhals Schema.
    
    Arguments:
        dataclass_type: A dataclass type.
        
    Returns:
        A Narwhals Schema representing the dataclass fields.
    """
    if not dataclasses.is_dataclass(dataclass_type):
        msg = f"{dataclass_type} is not a dataclass"
        raise TypeError(msg)
    
    # Get type hints which include annotations
    type_hints = get_type_hints(dataclass_type, include_extras=True)
    
    schema_dict = {}
    for field in dataclasses.fields(dataclass_type):
        field_name = field.name
        field_type = type_hints[field_name]
        
        # Extract metadata from field (if using Annotated types)
        metadata = getattr(field_type, "__metadata__", ())
        
        schema_dict[field_name] = dataclass_field_to_nw_type(field_type, metadata)
    
    return Schema(schema_dict)


def dataclass_field_to_nw_type(  # noqa: C901, PLR0911
    annotation: type[Any],
    metadata: tuple[Any, ...] = (),
) -> DType:
    """Convert a dataclass field type to a Narwhals DType.
    
    Arguments:
        annotation: The type annotation of the field.
        metadata: Optional metadata associated with the field.
        
    Returns:
        A Narwhals DType representing the field's type.
    """
    # Handle Optional types
    if is_optional_type(annotation):
        inner_type, inner_metadata = unwrap_optional(annotation)
        return dataclass_field_to_nw_type(inner_type, inner_metadata or metadata)
    
    # Handle list types
    list_result = parse_list_type(annotation)
    if list_result is not None:
        inner_type, inner_metadata = list_result
        return nw.List(inner=dataclass_field_to_nw_type(inner_type, inner_metadata))
    
    # Handle nested dataclasses (Struct)
    if dataclasses.is_dataclass(annotation):
        type_hints = get_type_hints(annotation, include_extras=True)
        return nw.Struct(
            [
                nw.Field(
                    name=field.name,
                    dtype=dataclass_field_to_nw_type(
                        type_hints[field.name],
                        getattr(type_hints[field.name], "__metadata__", ()),
                    ),
                )
                for field in dataclasses.fields(annotation)
            ]
        )
    
    # Handle integer with constraints
    if annotation is int:
        if has_integer_constraints(metadata):
            return parse_integer_constraints(metadata)
        return nw.Int64()
    
    # Try parsing as basic Python type
    python_dtype = parse_python_type(annotation, metadata)
    if python_dtype is not None:
        return python_dtype
    
    # If we reach here, the type is not supported
    msg = f"Unsupported type: {annotation}"
    raise NotImplementedError(msg)


__all__ = ("dataclass_to_nw_schema", "dataclass_field_to_nw_type")

