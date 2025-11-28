from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import narwhals as nw
from pydantic import BaseModel

from tests.pydantic.utils import model_to_nw_schema

if TYPE_CHECKING:
    from anyschema.parsers import ParserPipeline


def test_parse_string_literal(auto_pipeline: ParserPipeline) -> None:
    class UserModel(BaseModel):
        username: str
        role: Literal["admin", "user", "guest"]
        status: Literal["active", "inactive", "pending"]

    schema = model_to_nw_schema(UserModel, pipeline=auto_pipeline)

    assert schema["username"] == nw.String()
    assert schema["role"] == nw.Enum(["admin", "user", "guest"])
    assert schema["status"] == nw.Enum(["active", "inactive", "pending"])


def test_parse_mixed_literal_types(auto_pipeline: ParserPipeline) -> None:
    class ConfigModel(BaseModel):
        name: str
        log_level: Literal["debug", "info", "warning", "error"]
        max_retries: Literal[1, 2, 3, 5, 10]
        enabled: Literal[True, False]

    schema = model_to_nw_schema(ConfigModel, pipeline=auto_pipeline)

    assert schema["name"] == nw.String()
    assert schema["log_level"] == nw.Enum(["debug", "info", "warning", "error"])
    assert schema["max_retries"] == nw.Enum([1, 2, 3, 5, 10])
    assert schema["enabled"] == nw.Enum([True, False])


def test_parse_literal_with_optional(auto_pipeline: ParserPipeline) -> None:
    class ProductModel(BaseModel):
        name: str
        category: Literal["electronics", "clothing", "food"] | None
        priority: Literal["high", "medium", "low"]

    schema = model_to_nw_schema(ProductModel, pipeline=auto_pipeline)

    assert schema["name"] == nw.String()
    assert schema["category"] == nw.Enum(["electronics", "clothing", "food"])
    assert schema["priority"] == nw.Enum(["high", "medium", "low"])


def test_parse_nested_model_with_literal(auto_pipeline: ParserPipeline) -> None:
    class AddressModel(BaseModel):
        street: str
        country: Literal["US", "UK", "CA", "AU"]

    class PersonModel(BaseModel):
        name: str
        role: Literal["employee", "contractor", "intern"]
        address: AddressModel

    schema = model_to_nw_schema(PersonModel, pipeline=auto_pipeline)

    assert schema["name"] == nw.String()
    assert schema["role"] == nw.Enum(["employee", "contractor", "intern"])
    assert schema["address"] == nw.Struct(
        [
            nw.Field("street", nw.String()),
            nw.Field("country", nw.Enum(["US", "UK", "CA", "AU"])),
        ]
    )
