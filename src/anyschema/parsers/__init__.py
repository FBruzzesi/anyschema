from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Literal

from anyschema.parsers.annotated import AnnotatedParser
from anyschema.parsers.annotated_types import AnnotatedTypesParser
from anyschema.parsers.base import ParserChain, TypeParser
from anyschema.parsers.forward_ref import ForwardRefParser
from anyschema.parsers.py_types import PyTypeParser
from anyschema.parsers.pydantic_types import PydanticTypeParser
from anyschema.parsers.union_types import UnionTypeParser

if TYPE_CHECKING:
    from anyschema.typing import IntoParserChain, ModelType


@lru_cache(maxsize=16)
def create_parser_chain(
    parsers: IntoParserChain = "auto",
    *,
    model_type: ModelType = None,
) -> ParserChain:
    """Create a parser chain with the specified parsers.

    Arguments:
        parsers: Either "auto" to automatically select parsers based on model_type,
                or a sequence of parser instances.
        model_type: The type of model being parsed ("pydantic" or "python").
                   Only used when parsers="auto".

    Returns:
        A ParserChain instance with the configured parsers.
    """
    if parsers == "auto":
        return _create_auto_parser_chain(model_type)

    # User-provided parsers
    parser_list = list(parsers)
    chain = ParserChain(parser_list)

    # Wire up the parser_chain reference for parsers that need it
    for parser in parser_list:
        parser.parser_chain = chain

    return chain


def _create_auto_parser_chain(model_type: Literal["pydantic", "python"] | None) -> ParserChain:
    """Create a parser chain with automatically selected parsers.

    Arguments:
        model_type: The type of model being parsed.

    Returns:
        A ParserChain instance with automatically selected parsers.
    """
    # Create parser instances (without chain reference yet)
    forward_ref_parser = ForwardRefParser()
    union_parser = UnionTypeParser()
    annotated_parser = AnnotatedParser()
    annotated_types_parser = AnnotatedTypesParser()
    python_parser = PyTypeParser()
    pydantic_parser = PydanticTypeParser()

    # Order matters! More specific parsers should come first:
    # 1. ForwardRefParser - resolves ForwardRef to actual types (MUST be first!)
    # 2. UnionTypeParser - handles Union/Optional and extracts the real type
    # 3. AnnotatedParser - extracts typing.Annotated and its metadata
    # 4. AnnotatedTypesParser - refines types based on metadata (e.g., int with constraints)
    # 5. PydanticTypeParser - handles Pydantic-specific types (if pydantic model)
    # 6. PyTypeParser - handles basic Python types (fallback)

    if model_type == "pydantic":
        parser_list = [
            forward_ref_parser,
            union_parser,
            annotated_parser,
            annotated_types_parser,
            pydantic_parser,
            python_parser,
        ]
    else:
        parser_list = [forward_ref_parser, union_parser, annotated_parser, annotated_types_parser, python_parser]

    chain = ParserChain(parser_list)

    # Wire up the parser_chain reference so parsers can recursively call the chain
    for parser in parser_list:
        parser.parser_chain = chain

    return chain


__all__ = (
    "AnnotatedParser",
    "AnnotatedTypesParser",
    "ForwardRefParser",
    "ParserChain",
    "PyTypeParser",
    "PydanticTypeParser",
    "TypeParser",
    "UnionTypeParser",
    "create_parser_chain",
)
