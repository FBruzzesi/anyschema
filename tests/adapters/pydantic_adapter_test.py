from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import pytest
from annotated_types import Ge
from pydantic import BaseModel, Field

from anyschema.adapters import pydantic_adapter

if TYPE_CHECKING:
    from anyschema.typing import FieldSpec


class SimpleModel(BaseModel):
    name: str
    age: int


class ModelWithMetadata(BaseModel):
    name: str
    age: Annotated[int, Field(ge=0)]


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (SimpleModel, (("name", str, ()), ("age", int, ()))),
        (ModelWithMetadata, (("name", str, ()), ("age", int, (Ge(ge=0),)))),
    ],
)
def test_pydantic_adapter(spec: type[BaseModel], expected: tuple[FieldSpec, ...]) -> None:
    result = tuple(pydantic_adapter(spec))
    assert result == expected
