from __future__ import annotations

from importlib import metadata

from anyschema._anyschema import AnySchema
from anyschema.parsers import (
    AnnotatedParser,
    ForwardRefParser,
    ParserChain,
    PyTypeParser,
    TypeParser,
    UnionTypeParser,
    create_parser_chain,
)

__title__ = __name__
__version__ = metadata.version(__title__)

__all__ = (
    "AnnotatedParser",
    "AnnotatedTypesParser",
    "AnySchema",
    "ForwardRefParser",
    "ParserChain",
    "PyTypeParser",
    "PydanticTypeParser",
    "TypeParser",
    "UnionTypeParser",
    "create_parser_chain",
)
