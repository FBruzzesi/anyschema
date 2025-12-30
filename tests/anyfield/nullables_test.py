from __future__ import annotations

from typing import Any, TypeAlias

import pytest

from anyschema import AnySchema

AnyDict: TypeAlias = dict[str, Any]


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ({}, ()),
        ({"id": int, "name": str}, (False, False)),
        ({"id": int, "name": str, "age": int}, (False, False, False)),
        ({"id": int, "name": str, "age": int | None}, (False, False, True)),
    ],
)
def test_nullables_named_false(spec: AnyDict, expected: tuple[bool, ...]) -> None:
    schema = AnySchema(spec=spec)
    result = schema.nullables()

    assert result == expected


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ({}, {}),
        ({"id": int, "name": str}, (False, False)),
        ({"id": int, "name": str, "age": int}, (False, False, False)),
        ({"id": int, "name": str, "age": int | None}, (False, False, True)),
    ],
)
def test_nullables_named_true(spec: AnyDict, expected: tuple[bool, ...]) -> None:
    schema = AnySchema(spec=spec)
    result = schema.nullables(named=True)

    assert result == dict(zip(spec, expected, strict=True))
