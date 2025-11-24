from __future__ import annotations

from collections.abc import Callable, Generator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from anyschema.parsers import ParserStep

if TYPE_CHECKING:
    from narwhals.schema import Schema
    from pydantic import BaseModel


IntoOrderedDict: TypeAlias = Mapping[str, type] | Sequence[tuple[str, type]]
"""An object that can be converted into a python [`OrderedDict`][ordered-dict].

We check for the object to be either a mapping or a sequence of sized 2 tuples.

[ordered-dict]: https://docs.python.org/3/library/collections.html#collections.OrderedDict
"""

IntoParserPipeline: TypeAlias = Literal["auto"] | Sequence[ParserStep]
"""An object that can be converted into a [`ParserPipeline`][anyschema.parsers.ParserPipeline].

Either "auto" or a sequence of [`ParserStep`][anyschema.parsers.ParserStep].
"""

Spec: TypeAlias = "Schema |  IntoOrderedDict | type[BaseModel]"
"""Input specification supported directly by [`AnySchema`][anyschema.AnySchema]."""

SpecType: TypeAlias = Literal["pydantic", "python"] | None
"""Specification type, either 'pydantic', 'python' or None.

Filled automatically based on the input.
"""

FieldName: TypeAlias = str
FieldType: TypeAlias = type
FieldMetadata: TypeAlias = tuple

FieldSpec: TypeAlias = tuple[FieldName, FieldType, FieldMetadata]
"""Field specification: alias for a tuple of `(str, type, tuple(metadata, ...))`."""

FieldSpecIterable: TypeAlias = Generator[FieldSpec, None, None]
"""Return type of an adapter."""

Adapter: TypeAlias = Callable[[Any], FieldSpecIterable]
"""Adapter expected signature.

An adapter is a callable that adapts a spec into field specifications.
"""
