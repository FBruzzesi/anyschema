from __future__ import annotations

from typing import TYPE_CHECKING

from narwhals import Schema

from anyschema.adapters import pydantic_adapter

if TYPE_CHECKING:
    from pydantic import BaseModel

    from anyschema.parsers import ParserPipeline


def model_to_nw_schema(spec: type[BaseModel], pipeline: ParserPipeline) -> Schema:
    return Schema({name: pipeline.parse(input_type, metadata) for name, input_type, metadata in pydantic_adapter(spec)})
