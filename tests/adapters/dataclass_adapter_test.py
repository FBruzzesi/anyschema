from __future__ import annotations

from dataclasses import dataclass, make_dataclass
from datetime import date
from typing import TYPE_CHECKING

import pytest

from anyschema.adapters import dataclass_adapter

if TYPE_CHECKING:
    from anyschema.typing import Dataclass


@dataclass
class Test:
    name: str
    age: int
    date_of_birth: date


@pytest.mark.parametrize(
    "spec",
    [
        Test,
        make_dataclass("Test", [("name", str), ("age", int), ("date_of_birth", date)]),
    ],
)
def test_into_ordered_dict_adapter(spec: Dataclass) -> None:
    expected = (("name", str, ()), ("age", int, ()), ("date_of_birth", date, ()))
    result = tuple(dataclass_adapter(spec))
    assert result == expected
