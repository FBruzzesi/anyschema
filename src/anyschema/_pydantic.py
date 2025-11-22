"""Pydantic model to Narwhals schema conversion using the new parser architecture."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from narwhals.schema import Schema

from anyschema.parsers import create_parser_chain

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic import BaseModel

    from anyschema.parsers.base import TypeParser


def model_to_nw_schema(
    model: type[BaseModel],
    parsers: Literal["auto"] | Sequence[TypeParser] = "auto",
) -> Schema:
    """Converts Pydantic model to Narwhals Schema.

    Arguments:
        model: The Pydantic model class or instance to convert.
        parsers: Either "auto" to automatically select parsers, or a sequence of parser instances.

    Returns:
        A Narwhals Schema representing the Pydantic model.
    """
    # Create the parser chain
    parser_chain = create_parser_chain(parsers, model_type="pydantic")

    # Parse each field
    schema_dict = {}
    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation
        metadata = tuple(field_info.metadata)

        # Use the parser chain to parse the field type (strict=True raises if unable to parse)
        dtype = parser_chain.parse(annotation, metadata, strict=True)
        schema_dict[field_name] = dtype

    return Schema(schema_dict)
