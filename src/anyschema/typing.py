from __future__ import annotations

from collections.abc import Callable, Generator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from anyschema.parsers import TypeParser

if TYPE_CHECKING:
    from narwhals.schema import Schema
    from pydantic import BaseModel


IntoOrderedDict: TypeAlias = Mapping[str, type] | Sequence[tuple[str, type]]
IntoParserPipeline: TypeAlias = Literal["auto"] | Sequence[TypeParser]

Spec: TypeAlias = "Schema |  IntoOrderedDict | type[BaseModel]"
SpecType: TypeAlias = Literal["pydantic", "python"] | None

FieldName: TypeAlias = str
FieldType: TypeAlias = type
FieldMetadata: TypeAlias = tuple
FieldSpec: TypeAlias = tuple[FieldName, FieldType, FieldMetadata]

FieldSpecIterable: TypeAlias = Generator[FieldSpec, None, None]
Adapter: TypeAlias = Callable[[Any], FieldSpecIterable]
