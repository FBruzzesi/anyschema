from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from anyschema import AnySchema

if TYPE_CHECKING:
    from anyschema.typing import Spec


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ({}, ()),
        ({"only_field": str}, ("only_field",)),
        ({"id": int, "name": str, "age": int}, ("id", "name", "age")),
    ],
)
def test_names(spec: Spec, expected: tuple[str, ...]) -> None:
    schema = AnySchema(spec=spec)
    result = schema.names()

    assert result == expected
