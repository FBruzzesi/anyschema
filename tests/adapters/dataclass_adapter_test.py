from __future__ import annotations

from dataclasses import dataclass, make_dataclass
from datetime import date
from typing import TYPE_CHECKING

import pytest
from pydantic.dataclasses import dataclass as pydantic_dataclass

from anyschema.adapters import dataclass_adapter

if TYPE_CHECKING:
    from anyschema.typing import DataclassType


class PersonIntoDataclass:
    name: str
    age: int
    date_of_birth: date


@pytest.mark.parametrize(
    "spec",
    [
        pydantic_dataclass(PersonIntoDataclass),
        dataclass(PersonIntoDataclass),
        make_dataclass("Test", [("name", str), ("age", int), ("date_of_birth", date)]),
    ],
)
def test_dataclass_adapter(spec: DataclassType) -> None:
    expected = (("name", str, ()), ("age", int, ()), ("date_of_birth", date, ()))
    result = tuple(dataclass_adapter(spec))
    assert result == expected
