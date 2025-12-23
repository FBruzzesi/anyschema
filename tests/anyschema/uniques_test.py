from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from anyschema import AnySchema
from tests.conftest import ProductORM, array_fixed_table

if TYPE_CHECKING:
    from anyschema.typing import Spec


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (array_fixed_table, (True, False, False)),
        (ProductORM, (True, False, False, False)),
    ],
)
def test_uniques_named_false(spec: Spec, expected: tuple[bool, ...]) -> None:
    schema = AnySchema(spec=spec)
    result = schema.uniques(named=False)

    assert result == expected


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (array_fixed_table, {"id": True, "coordinates": False, "matrix": False}),
        (
            ProductORM,
            {"id": True, "name": False, "price": False, "in_stock": False},
        ),
    ],
)
def test_uniques_named_true(spec: Spec, expected: dict[str, bool]) -> None:
    schema = AnySchema(spec=spec)
    result = schema.uniques(named=True)

    assert result == expected
