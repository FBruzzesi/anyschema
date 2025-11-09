from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any

from narwhals.schema import Schema

if TYPE_CHECKING:
    from narwhals.dtypes import DType


class FieldInfo(ABC):
    """Abstract base class for field information from different data structure libraries.
    
    This class provides a common interface for accessing field metadata regardless
    of whether it comes from Pydantic, dataclasses, attrs, or other sources.
    """
    
    @property
    @abstractmethod
    def annotation(self) -> type[Any]:
        """Get the type annotation of the field."""
        ...
    
    @property
    @abstractmethod
    def metadata(self) -> tuple[Any, ...]:
        """Get the metadata associated with the field."""
        ...


class SchemaParser(ABC):
    """Abstract base class for parsing data structures into Narwhals Schema.
    
    Each data structure library (Pydantic, dataclasses, etc.) should implement
    this interface to provide schema conversion functionality.
    """
    
    @abstractmethod
    def model_to_schema(self, model: Any) -> Schema:
        """Convert a model/dataclass to a Narwhals Schema.
        
        Arguments:
            model: The model or dataclass to convert.
            
        Returns:
            A Narwhals Schema representing the model's fields.
        """
        ...
    
    @abstractmethod
    def field_to_dtype(self, field_info: Any) -> DType:
        """Convert a field to a Narwhals DType.
        
        Arguments:
            field_info: The field information object.
            
        Returns:
            A Narwhals DType representing the field's type.
        """
        ...


__all__ = (
    "FieldInfo",
    "SchemaParser",
)

