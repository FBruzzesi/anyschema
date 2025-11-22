"""Pydantic model to Narwhals schema conversion using the new parser architecture."""

from __future__ import annotations

from typing import TYPE_CHECKING

from narwhals.schema import Schema

if TYPE_CHECKING:
    from pydantic import BaseModel

    from anyschema.parsers import ParserChain


def model_to_nw_schema(model: type[BaseModel], parser_chain: ParserChain) -> Schema:
    """Converts Pydantic model to Narwhals Schema.

    Arguments:
        model: The Pydantic model class or instance to convert.
        parser_chain: parser chain to use to convert each field from pydantic to narwhals dtype.

    Returns:
        A Narwhals Schema representing the Pydantic model.
    """
    return Schema(
        {
            field_name: parser_chain.parse(field_info.annotation, tuple(field_info.metadata))  # type: ignore[arg-type]
            for field_name, field_info in model.model_fields.items()
        }
    )
