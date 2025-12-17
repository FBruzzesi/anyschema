from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

import narwhals as nw
import pytest

from anyschema import AnyField

if TYPE_CHECKING:
    from collections.abc import Mapping

    from anyschema.typing import IntoAnyField


@pytest.mark.parametrize("dtype", [nw.String(), nw.Int32(), nw.Array(nw.Int32(), shape=(3, 2))])
@pytest.mark.parametrize("nullable", [True, False, None])
@pytest.mark.parametrize("unique", [True, False, None])
@pytest.mark.parametrize("description", ["some description", None])
@pytest.mark.parametrize("metadata", [{"min": 0, "max": 150}, None])
def test_anyfield(
    dtype: nw.dtypes.DType,
    *,
    nullable: bool | None,
    unique: bool | None,
    description: str | None,
    metadata: Mapping[str, Any] | None,
) -> None:
    kwargs: IntoAnyField = {
        "name": "id",
        "dtype": dtype,
        "nullable": nullable,
        "unique": unique,
        "description": description,
        "metadata": metadata,
    }
    expected: IntoAnyField = {
        "name": "id",
        "dtype": dtype,
        "nullable": nullable if nullable is not None else False,
        "unique": unique if unique is not None else False,
        "description": description,
        "metadata": metadata if metadata is not None else {},
    }
    into_field = {k: v for k, v in kwargs.items() if v is not None}
    field = AnyField(**into_field)
    assert asdict(field) == expected

    field2 = AnyField(**into_field)

    assert field == field2
    assert hash(field) == hash(field2)


@pytest.mark.parametrize(
    ("field1_kwargs", "field2_kwargs"),
    [
        (
            {"name": "id", "dtype": nw.Int64()},
            {"name": "user_id", "dtype": nw.Int64()},
        ),
        (
            {"name": "age", "dtype": nw.Int64()},
            {"name": "age", "dtype": nw.Int32()},
        ),
        (
            {"name": "email", "dtype": nw.String(), "nullable": True},
            {"name": "email", "dtype": nw.String(), "nullable": False},
        ),
        (
            {"name": "username", "dtype": nw.String(), "unique": False},
            {"name": "username", "dtype": nw.String(), "unique": True},
        ),
        (
            {"name": "score", "dtype": nw.Float64(), "metadata": {"min": 0}},
            {"name": "score", "dtype": nw.Float64(), "metadata": {"max": 100}},
        ),
    ],
)
def test_field_unequal_fields(field1_kwargs: IntoAnyField, field2_kwargs: IntoAnyField) -> None:
    field1, field2 = AnyField(**field1_kwargs), AnyField(**field2_kwargs)
    assert field1 != field2


@pytest.mark.parametrize(
    "other_value",
    [
        "not a field",
        42,
        None,
        {"name": "test"},
        [],
        nw.String(),
    ],
)
def test_field_equality_with_non_field(other_value: object) -> None:
    """Test that Field is not equal to non-Field objects."""
    field = AnyField(name="test", dtype=nw.String())
    assert field != other_value


@pytest.mark.parametrize(
    ("field_configs", "expected_unique_count"),
    [
        (
            [
                {"name": "id", "dtype": nw.Int64()},
                {"name": "id", "dtype": nw.Int64()},  # Duplicate
                {"name": "name", "dtype": nw.String()},
            ],
            2,
        ),
        (
            [
                {"name": "a", "dtype": nw.String()},
                {"name": "b", "dtype": nw.String()},
                {"name": "c", "dtype": nw.String()},
            ],
            3,
        ),
        (
            [
                {"name": "id", "dtype": nw.Int64(), "nullable": True},
                {"name": "id", "dtype": nw.Int64(), "nullable": True},  # Duplicate
                {"name": "id", "dtype": nw.Int64(), "nullable": False},  # Different
            ],
            2,
        ),
    ],
)
def test_field_use_in_set(field_configs: list[dict], expected_unique_count: int) -> None:
    """Test that Field instances work correctly in sets."""
    fields = [AnyField(**config) for config in field_configs]  # type: ignore[arg-type]
    field_set = set(fields)
    assert len(field_set) == expected_unique_count


@pytest.mark.parametrize(
    ("field_kwargs", "expected_description"),
    [
        ({"name": "user_id", "dtype": nw.Int64(), "description": "Unique user identifier"}, "Unique user identifier"),
        ({"name": "user_id", "dtype": nw.Int64(), "description": None}, None),
        ({"name": "test", "dtype": nw.String()}, None),  # Default
        ({"name": "email", "dtype": nw.String(), "description": ""}, ""),  # Empty string
    ],
)
def test_field_description_values(field_kwargs: IntoAnyField, expected_description: str | None) -> None:
    """Test Field creation with various description values."""
    field = AnyField(**field_kwargs)  # type: ignore[arg-type]
    assert field.description == expected_description
