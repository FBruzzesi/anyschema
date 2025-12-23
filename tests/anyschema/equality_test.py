from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from anyschema import AnySchema

if TYPE_CHECKING:
    from anyschema.typing import Spec


@pytest.mark.parametrize(
    "spec",
    [
        {"name": str, "age": int},
        {"users": list[str], "counts": dict[str, int]},
    ],
)
def test_equal(spec: Spec) -> None:
    assert AnySchema(spec=spec) == AnySchema(spec=spec)


@pytest.mark.parametrize(
    ("spec1", "spec2"),
    [
        ({"name": str, "age": int}, {"age": int, "name": str}),
        ({"name": str, "age": int}, {"name": str}),
        ({"value": int}, {"value": float}),
        ({"name": str}, {"name": str | None}),
    ],
)
def test_not_equal(spec1: Spec, spec2: Spec) -> None:
    schema1 = AnySchema(spec=spec1)
    schema2 = AnySchema(spec=spec2)

    assert schema1 != schema2


@pytest.mark.parametrize(
    "other",
    [
        {"name": str},
        "not a schema",
        42,
        None,
    ],
)
def test_equality_with_non_anyschema_object(other: Any) -> None:
    schema = AnySchema(spec={"name": str})

    assert schema != other
