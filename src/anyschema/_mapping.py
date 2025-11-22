"""Mapping to Narwhals schema conversion."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from narwhals.schema import Schema

from anyschema.parsers import create_parser_chain

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from anyschema.parsers import TypeParser


def mapping_to_nw_schema(
    model: Mapping[str, type],
    parsers: Literal["auto"] | Sequence[TypeParser] = "auto",
) -> Schema:
    """Converts Pydantic model to Narwhals Schema.

    Arguments:
        model: The Pydantic model class or instance to convert.
        parsers: Either "auto" to automatically select parsers, or a sequence of parser instances.

    Returns:
        A Narwhals Schema representing the Pydantic model.
    """
    parser_chain = create_parser_chain(parsers, model_type="python")

    return Schema({name: parser_chain.parse(input_type) for name, input_type in model.items()})
