from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from anyschema._dependencies import ANNOTATED_TYPES_AVAILABLE
from anyschema.parsers._annotated import AnnotatedParser
from anyschema.parsers._base import ParserChain, TypeParser
from anyschema.parsers._builtin import PyTypeParser
from anyschema.parsers._forward_ref import ForwardRefParser
from anyschema.parsers._union import UnionTypeParser

if TYPE_CHECKING:
    from collections.abc import Sequence

    from anyschema.typing import IntoParserChain, SpecType

__all__ = (
    "AnnotatedParser",
    "ForwardRefParser",
    "ParserChain",
    "PyTypeParser",
    "TypeParser",
    "UnionTypeParser",
    "create_parser_chain",
)


@lru_cache(maxsize=16)
def create_parser_chain(parsers: IntoParserChain = "auto", *, spec_type: SpecType = None) -> ParserChain:
    """Create a parser chain with the specified parsers.

    Arguments:
        parsers: Either "auto" to automatically select parsers based on spec_type,
            or a sequence of parser instances.
        spec_type: The type of model being parsed ("pydantic" or "python"). Only used when parsers="auto".

    Returns:
        A ParserChain instance with the configured parsers.
    """
    parsers_ = _auto_create_parsers(spec_type) if parsers == "auto" else tuple(parsers)
    chain = ParserChain(parsers_)

    # Wire up the parser_chain reference for parsers that need it
    # TODO(FBruzzesi): Is there a better way to achieve this?
    for parser in parsers_:
        parser.parser_chain = chain

    return chain


def _auto_create_parsers(spec_type: SpecType) -> Sequence[TypeParser]:
    """Create a parser chain with automatically selected parsers.

    Arguments:
        spec_type: The type of model being parsed.

    Returns:
        A ParserChain instance with automatically selected parsers.
    """
    # Create parser instances without chain reference (yet)
    forward_ref_parser = ForwardRefParser()
    union_parser = UnionTypeParser()
    annotated_parser = AnnotatedParser()
    python_parser = PyTypeParser()

    # Order matters! More specific parsers should come first:
    # 1. ForwardRefParser - resolves ForwardRef to actual types (MUST be first!)
    # 2. UnionTypeParser - handles Union/Optional and extracts the real type
    # 3. AnnotatedParser - extracts typing.Annotated and its metadata
    # 4. AnnotatedTypesParser - refines types based on metadata (e.g., int with constraints)
    # 5. PydanticTypeParser - handles Pydantic-specific types (if pydantic model)
    # 6. PyTypeParser - handles basic Python types (fallback)
    parsers: Sequence[TypeParser]
    if spec_type == "pydantic":
        from anyschema.parsers.annotated_types import AnnotatedTypesParser
        from anyschema.parsers.pydantic import PydanticTypeParser

        annotated_types_parser = AnnotatedTypesParser()
        pydantic_parser = PydanticTypeParser()

        parsers = (
            forward_ref_parser,
            union_parser,
            annotated_parser,
            annotated_types_parser,
            pydantic_parser,
            python_parser,
        )
    elif ANNOTATED_TYPES_AVAILABLE:
        from anyschema.parsers.annotated_types import AnnotatedTypesParser

        annotated_types_parser = AnnotatedTypesParser()
        parsers = (forward_ref_parser, union_parser, annotated_parser, annotated_types_parser, python_parser)
    else:  # pragma: no cover
        parsers = (forward_ref_parser, union_parser, annotated_parser, python_parser)
    return parsers
