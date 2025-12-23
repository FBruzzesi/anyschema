from __future__ import annotations

from anyschema import AnyField, AnySchema


def test_fields_correct_keys_and_values() -> None:
    spec = {"id": int, "name": str, "age": int}
    schema = AnySchema(spec=spec)
    result = schema.fields

    assert isinstance(result, dict)
    assert result.keys() == spec.keys()

    for field_name, field_obj in result.items():
        assert isinstance(field_obj, AnyField)
        assert field_obj.name == field_name


def test_fields_empty_schema() -> None:
    schema = AnySchema(spec={})
    result = schema.fields

    assert result == {}


def test_fields_returns_copy() -> None:
    schema = AnySchema(spec={"id": int, "name": str})
    result1 = schema.fields
    result2 = schema.fields

    assert result1 is not result2  # Should return a new dict each time
    assert result1 == result2  # But with equal contents


def test_fields_modification_does_not_affect_schema() -> None:
    schema = AnySchema(spec={"id": int, "name": str})
    fields = schema.fields

    # Modify the returned dict
    fields["new_field"] = AnyField(name="new_field", dtype=schema.field("id").dtype)

    # Original schema should be unchanged
    assert "new_field" not in schema.names()


def test_fields_with_nullable_and_metadata() -> None:
    schema = AnySchema(spec={"id": int, "name": str, "age": int | None})
    fields = schema.fields

    assert fields["id"].nullable is False
    assert fields["name"].nullable is False
    assert fields["age"].nullable is True
