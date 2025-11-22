"""Mapping to Narwhals schema conversion."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

from narwhals.schema import Schema

if TYPE_CHECKING:
    from anyschema.parsers import ParserChain
    from anyschema.typing import IntoOrderedDict


def mapping_to_nw_schema(schema: IntoOrderedDict, parser_chain: ParserChain) -> Schema:
    """Converts python Mapping or Sequence to Narwhals Schema.

    Arguments:
        schema: The python Mapping or Sequence to convert.
        parser_chain: parser chain to use to convert each type from python to narwhals dtype.

    Returns:
        A Narwhals Schema representing the Pydantic model.
    """
    return Schema(
        {name: parser_chain.parse(input_type, metadata=()) for name, input_type in OrderedDict(schema).items()}
    )
