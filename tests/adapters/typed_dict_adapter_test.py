from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, TypedDict

import pytest

from anyschema.adapters import typed_dict_adapter

if TYPE_CHECKING:
    from anyschema.typing import FieldSpec, TypedDictType


class PersonTypedDict(TypedDict):
    name: str
    age: int
    date_of_birth: date


@pytest.mark.parametrize(
    "spec",
    [
        PersonTypedDict,
    ],
)
def test_typed_dict_adapter(spec: TypedDictType) -> None:
    expected: tuple[FieldSpec, ...] = (("name", str, (), {}), ("age", int, (), {}), ("date_of_birth", date, (), {}))
    result = tuple(typed_dict_adapter(spec))
    assert result == expected
