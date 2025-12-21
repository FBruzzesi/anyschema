from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import attrs
from pydantic import BaseModel
from pydantic import Field as PydanticField

from anyschema import AnySchema


def test_pydantic_field_metadata_not_mutated_by_optional() -> None:
    """Test that parsing Optional fields doesn't mutate Pydantic Field metadata."""

    class User(BaseModel):
        name: str = PydanticField(json_schema_extra={"description": "User name"})
        email: Optional[str] = PydanticField(json_schema_extra={"format": "email"})

    name_metadata_before = User.model_fields["name"].json_schema_extra
    email_metadata_before = User.model_fields["email"].json_schema_extra

    schema = AnySchema(spec=User)

    assert schema.fields["name"].nullable is False
    assert schema.fields["email"].nullable is True

    name_metadata_after = User.model_fields["name"].json_schema_extra
    email_metadata_after = User.model_fields["email"].json_schema_extra

    # !NOTE: Ensure original metadata was not mutated
    assert name_metadata_before == name_metadata_after
    assert email_metadata_before == email_metadata_after

    # !NOTE: isinstance check is for type checking purposes
    assert isinstance(name_metadata_after, dict)
    assert "anyschema/nullable" not in name_metadata_after

    assert isinstance(email_metadata_after, dict)
    assert "anyschema/nullable" not in email_metadata_after


def test_pydantic_field_metadata_with_explicit_anyschema_keys() -> None:
    """Test that existing anyschema/* keys in Pydantic metadata are not modified."""

    class Product(BaseModel):
        id: int = PydanticField(
            json_schema_extra={
                "anyschema/nullable": False,
                "anyschema/unique": True,
                "description": "Product ID",
            }
        )
        name: Optional[str] = PydanticField(
            json_schema_extra={
                "anyschema/nullable": True,  # Explicitly set
                "max_length": 100,
            }
        )

    schema = AnySchema(spec=Product)

    assert schema.fields["id"].nullable is False
    assert schema.fields["id"].unique is True

    id_metadata_after = Product.model_fields["id"].json_schema_extra
    name_metadata_after = Product.model_fields["name"].json_schema_extra

    assert id_metadata_after == {
        "anyschema/nullable": False,
        "anyschema/unique": True,
        "description": "Product ID",
    }
    assert name_metadata_after == {
        "anyschema/nullable": True,
        "max_length": 100,
    }


def test_dataclass_field_metadata_not_mutated() -> None:
    """Test that parsing doesn't mutate dataclass field metadata."""

    @dataclass
    class Person:
        name: str = field(metadata={"description": "Person name"})
        email: Optional[str] = field(metadata={"format": "email"})

    # Get original metadata (dataclass fields are in __dataclass_fields__)
    name_field_before = Person.__dataclass_fields__["name"]
    email_field_before = Person.__dataclass_fields__["email"]
    name_metadata_before = dict(name_field_before.metadata)
    email_metadata_before = dict(email_field_before.metadata)

    schema = AnySchema(spec=Person)

    assert schema.fields["name"].nullable is False
    assert schema.fields["email"].nullable is True

    name_field_after = Person.__dataclass_fields__["name"]
    email_field_after = Person.__dataclass_fields__["email"]

    # !NOTE: Original metadata should not be mutated
    assert dict(name_field_after.metadata) == name_metadata_before
    assert dict(email_field_after.metadata) == email_metadata_before

    assert "anyschema/nullable" not in name_field_after.metadata
    assert "anyschema/nullable" not in email_field_after.metadata


def test_attrs_field_metadata_not_mutated() -> None:
    """Test that parsing doesn't mutate attrs field metadata."""

    @attrs.define
    class Book:
        title: str = attrs.field(metadata={"description": "Book title"})
        isbn: Optional[str] = attrs.field(metadata={"format": "isbn"})

    # Get original metadata
    attrs_fields = attrs.fields(Book)
    title_field_before = next(f for f in attrs_fields if f.name == "title")
    isbn_field_before = next(f for f in attrs_fields if f.name == "isbn")
    title_metadata_before = dict(title_field_before.metadata)
    isbn_metadata_before = dict(isbn_field_before.metadata)

    schema = AnySchema(spec=Book)

    assert schema.fields["title"].nullable is False
    assert schema.fields["isbn"].nullable is True

    # Get metadata after
    attrs_fields_after = attrs.fields(Book)
    title_field_after = next(f for f in attrs_fields_after if f.name == "title")
    isbn_field_after = next(f for f in attrs_fields_after if f.name == "isbn")

    # !NOTE: Original metadata should not be mutated
    assert dict(title_field_after.metadata) == title_metadata_before
    assert dict(isbn_field_after.metadata) == isbn_metadata_before

    assert "anyschema/nullable" not in title_field_after.metadata
    assert "anyschema/nullable" not in isbn_field_after.metadata


def test_dict_spec_is_safe() -> None:
    """Test that dict specs work correctly (they don't share metadata)."""
    spec = {"id": int, "name": Optional[str]}

    schema1 = AnySchema(spec=spec)
    schema2 = AnySchema(spec=spec)

    assert schema1.fields["name"].nullable is True
    assert schema2.fields["name"].nullable is True

    assert spec == {"id": int, "name": Optional[str]}
