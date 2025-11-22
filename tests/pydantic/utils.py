from __future__ import annotations

from typing import TYPE_CHECKING

from narwhals import Schema

from anyschema.adapters import pydantic_adapter

if TYPE_CHECKING:
    from pydantic import BaseModel

    from anyschema.parsers import ParserChain


def model_to_nw_schema(spec: type[BaseModel], parser_chain: ParserChain) -> Schema:
    return Schema(
        {name: parser_chain.parse(input_type, metadata) for name, input_type, metadata in pydantic_adapter(spec)}
    )
