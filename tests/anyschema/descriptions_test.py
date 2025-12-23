from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from anyschema import AnySchema
from tests.conftest import DataclassEventWithTimeMetadata, PydanticStudent, user_table

if TYPE_CHECKING:
    from anyschema.typing import Spec


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (PydanticStudent, ("Student full name", None, "Student age in years", None, None)),
        (DataclassEventWithTimeMetadata, ("Event name", None, "Scheduled time", None, None)),
        (user_table, ("Primary key", None, "User age", None)),
    ],
)
def test_descriptions_named_false(spec: Spec, expected: tuple[str | None, ...]) -> None:
    schema = AnySchema(spec=spec)
    result = schema.descriptions(named=False)

    assert result == expected


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (
            PydanticStudent,
            {
                "name": "Student full name",
                "date_of_birth": None,
                "age": "Student age in years",
                "classes": None,
                "has_graduated": None,
            },
        ),
        (
            DataclassEventWithTimeMetadata,
            {
                "name": "Event name",
                "created_at": None,
                "scheduled_at": "Scheduled time",
                "started_at": None,
                "completed_at": None,
            },
        ),
        (user_table, {"id": "Primary key", "name": None, "age": "User age", "email": None}),
    ],
)
def test_descriptions_named_true(spec: Spec, expected: dict[str, str | None]) -> None:
    schema = AnySchema(spec=spec)
    result = schema.descriptions(named=True)

    assert result == expected
