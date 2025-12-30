from __future__ import annotations

import pytest

from anyschema import AnyField, AnySchema


def test_field_correct_attributes() -> None:
    schema = AnySchema(spec={"id": int, "name": str, "age": int | None})

    id_field = schema.field("id")
    assert isinstance(id_field, AnyField)
    assert id_field.name == "id"
    assert id_field.nullable is False

    age_field = schema.field("age")
    assert isinstance(age_field, AnyField)
    assert age_field.name == "age"
    assert age_field.nullable is True


def test_field_raises_keyerror_for_missing_field() -> None:
    schema = AnySchema(spec={"id": int, "name": str})

    with pytest.raises(KeyError):
        schema.field("non_existent")


def test_field_with_all_field_names() -> None:
    spec = {"id": int, "name": str, "age": int, "active": bool}
    schema = AnySchema(spec=spec)

    for field_name in spec:
        field = schema.field(field_name)
        assert field.name == field_name
