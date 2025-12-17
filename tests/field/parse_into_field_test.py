from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Optional

import narwhals as nw
import pytest
from annotated_types import Gt, Lt
from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import Column, Integer, MetaData, String, Table

from anyschema import AnyField, AnySchema
from anyschema.parsers import make_pipeline
from tests.conftest import AttrsBookWithMetadata, AttrsPerson, user_table


@pytest.mark.parametrize(
    ("name", "py_type", "expected_dtype"),
    [
        ("int_field", int, nw.Int64()),
        ("str_field", str, nw.String()),
        ("float_field", float, nw.Float64()),
        ("bool_field", bool, nw.Boolean()),
        ("list_int", list[int], nw.List(nw.Int64())),
        ("list_str", list[str], nw.List(nw.String())),
        ("list_float", list[float], nw.List(nw.Float64())),
    ],
)
def test_parse_field(name: str, py_type: type, expected_dtype: nw.dtypes.DType) -> None:
    pipeline = make_pipeline()
    field = pipeline.parse_field(name, py_type, (), {})

    assert field == AnyField(name=name, dtype=expected_dtype)


@pytest.mark.parametrize(
    ("name", "py_type", "expected_dtype"),
    [
        ("opt_int", Optional[int], nw.Int64()),
        ("opt_str", Optional[str], nw.String()),
        ("opt_float", Optional[float], nw.Float64()),
        ("opt_bool", Optional[bool], nw.Boolean()),
        ("union_int", int | None, nw.Int64()),
        ("union_str", str | None, nw.String()),
    ],
)
def test_parse_field_nullable_type(name: str, py_type: type, expected_dtype: nw.dtypes.DType) -> None:
    pipeline = make_pipeline()
    field = pipeline.parse_field(name, py_type, (), {})

    assert field == AnyField(name=name, dtype=expected_dtype, nullable=True)


@pytest.mark.parametrize(
    ("nullable_value", "expected_nullable"),
    [
        (True, True),
        (False, False),
    ],
)
def test_parse_field_nullable_metadata(nullable_value: bool, expected_nullable: bool) -> None:  # noqa: FBT001
    pipeline = make_pipeline()
    field = pipeline.parse_field("test", int, (), {"__anyschema_metadata__": {"nullable": nullable_value}})

    assert field.nullable is expected_nullable


def test_parse_field_nullable_metadata_overwrite() -> None:
    # !NOTE: Test that explicit nullable=False overrides Optional type
    pipeline = make_pipeline()
    field = pipeline.parse_field("test", Optional[str], (), {"__anyschema_metadata__": {"nullable": False}})

    assert field == AnyField(name="test", dtype=nw.String(), nullable=False)


@pytest.mark.parametrize(
    ("unique_value", "expected_unique"),
    [
        (True, True),
        (False, False),
    ],
)
def test_parse_field_unique(unique_value: bool, expected_unique: bool) -> None:  # noqa: FBT001
    pipeline = make_pipeline()
    field = pipeline.parse_field("test", str, (), {"__anyschema_metadata__": {"unique": unique_value}})

    assert field.unique is expected_unique


def test_anyschema_metadata_filtered_from_field_metadata() -> None:
    """Test that __anyschema_metadata__ is filtered from Field.metadata."""
    pipeline = make_pipeline()
    field = pipeline.parse_field(
        "test",
        int,
        (),
        {
            "__anyschema_metadata__": {
                "nullable": False,
                "unique": True,
                "time_zone": "UTC",
            },
            "description": "A test field",
            "custom_key": "custom_value",
        },
    )

    # __anyschema_metadata__ should not be in field.metadata
    assert "__anyschema_metadata__" not in field.metadata

    # Custom metadata should be preserved
    assert field.metadata == {"description": "A test field", "custom_key": "custom_value"}


def test_custom_metadata_preserved() -> None:
    """Test that custom metadata is preserved in Field."""
    pipeline = make_pipeline()
    custom_metadata = {
        "description": "User email address",
        "format": "email",
        "example": "user@example.com",
        "max_length": 255,
    }
    field = pipeline.parse_field("email", str, (), custom_metadata)

    assert field.metadata == custom_metadata


@pytest.mark.parametrize(
    ("spec", "expected_field_names"),
    [
        ({"id": int}, ["id"]),
        ({"id": int, "name": str}, ["id", "name"]),
        ({"id": int, "name": str, "age": int, "active": bool}, ["id", "name", "age", "active"]),
    ],
)
def test_anyschema_fields_contains_all_spec_fields(spec: dict[str, type], expected_field_names: list[str]) -> None:
    """Test that all fields from spec are in the fields attribute."""
    schema = AnySchema(spec=spec)

    assert len(schema.fields) == len(expected_field_names)
    for field_name in expected_field_names:
        assert field_name in schema.fields
        assert isinstance(schema.fields[field_name], AnyField)
        assert schema.fields[field_name].name == field_name


def test_anyschema_fields_are_field_instances() -> None:
    """Test that all values in fields dict are AnyField instances."""
    schema = AnySchema(spec={"id": int, "name": str, "email": Optional[str]})

    for field_name, field in schema.fields.items():
        assert isinstance(field, AnyField)
        assert field.name == field_name


def test_pydantic_student_fields(pydantic_student_cls: type[BaseModel]) -> None:
    """Test parsing PydanticStudent fixture."""
    schema = AnySchema(spec=pydantic_student_cls)

    # Check that all fields are present
    assert "name" in schema.fields
    assert "date_of_birth" in schema.fields
    assert "age" in schema.fields
    assert "classes" in schema.fields
    assert "has_graduated" in schema.fields

    # Check field properties
    name_field = schema.fields["name"]
    assert name_field.dtype == nw.String()
    assert name_field.nullable is False  # Default is now False

    age_field = schema.fields["age"]
    assert age_field.dtype == nw.UInt64()  # PositiveInt maps to UInt64


def test_pydantic_with_explicit_metadata() -> None:
    """Test Pydantic model with explicit nullable and unique metadata."""

    class UserWithMetadata(BaseModel):
        id: int = PydanticField(json_schema_extra={"__anyschema_metadata__": {"nullable": False, "unique": True}})
        username: str = PydanticField(
            json_schema_extra={"__anyschema_metadata__": {"unique": True}, "description": "User's login name"}
        )
        email: Optional[str] = PydanticField(json_schema_extra={"format": "email"})

    schema = AnySchema(spec=UserWithMetadata)

    # Check id field
    id_field = schema.fields["id"]
    assert id_field.nullable is False
    assert id_field.unique is True
    assert "__anyschema_metadata__" not in id_field.metadata

    # Check username field
    username_field = schema.fields["username"]
    assert username_field.unique is True
    assert username_field.metadata == {"description": "User's login name"}

    # Check email field
    email_field = schema.fields["email"]
    assert email_field.nullable is True
    assert email_field.metadata == {"format": "email"}


def test_pydantic_with_custom_metadata() -> None:
    """Test that custom metadata from Pydantic is preserved."""

    class ProductWithMetadata(BaseModel):
        name: str = PydanticField(json_schema_extra={"max_length": 100, "description": "Product name"})
        price: float = PydanticField(json_schema_extra={"min": 0, "currency": "USD"})

    schema = AnySchema(spec=ProductWithMetadata)

    name_field = schema.fields["name"]
    assert name_field.metadata == {"max_length": 100, "description": "Product name"}

    price_field = schema.fields["price"]
    assert price_field.metadata == {"min": 0, "currency": "USD"}


def test_sqlalchemy_user_table() -> None:
    """Test parsing user_table from conftest."""
    schema = AnySchema(spec=user_table)

    # Check id field - primary_key, not nullable
    id_field = schema.fields["id"]
    assert id_field.nullable is False
    assert id_field.dtype == nw.Int32()

    # Check email field - explicitly nullable
    email_field = schema.fields["email"]
    assert email_field.nullable is True


def test_sqlalchemy_auto_detects_nullable() -> None:
    """Test that SQLAlchemy nullable property is auto-detected."""
    metadata = MetaData()
    test_table = Table(
        "test",
        metadata,
        Column("not_null", Integer, nullable=False),
        Column("nullable", Integer, nullable=True),
        Column("default_nullable", Integer),  # Default is nullable
    )

    schema = AnySchema(spec=test_table)

    assert schema.fields["not_null"].nullable is False
    assert schema.fields["nullable"].nullable is True
    assert schema.fields["default_nullable"].nullable is True


def test_sqlalchemy_auto_detects_unique() -> None:
    """Test that SQLAlchemy unique constraint is auto-detected."""
    metadata = MetaData()
    test_table = Table(
        "test",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("unique_username", String(50), unique=True),
        Column("normal_field", String(50)),
    )

    schema = AnySchema(spec=test_table)

    # unique=True should be detected
    assert schema.fields["unique_username"].unique is True
    # Normal field should not be unique
    assert schema.fields["normal_field"].unique is False


def test_attrs_person() -> None:
    """Test parsing AttrsPerson fixture."""
    schema = AnySchema(spec=AttrsPerson)

    # Check that all fields are present
    assert "name" in schema.fields
    assert "age" in schema.fields
    assert "date_of_birth" in schema.fields
    assert "is_active" in schema.fields
    assert "classes" in schema.fields
    assert "grades" in schema.fields

    # Check field types
    assert schema.fields["name"].dtype == nw.String()
    assert schema.fields["age"].dtype == nw.Int64()
    assert schema.fields["is_active"].dtype == nw.Boolean()


def test_attrs_with_metadata() -> None:
    """Test attrs class with metadata."""
    schema = AnySchema(spec=AttrsBookWithMetadata)

    title_field = schema.fields["title"]
    assert title_field.metadata == {"description": "Book title"}

    author_field = schema.fields["author"]
    assert author_field.metadata == {"max_length": 100}


def test_dataclass_basic() -> None:
    """Test parsing basic dataclass."""

    @dataclass
    class Person:
        name: str
        age: int
        email: Optional[str]

    schema = AnySchema(spec=Person)

    num_fields = 3
    assert len(schema.fields) == num_fields
    assert schema.fields["name"].dtype == nw.String()
    assert schema.fields["age"].dtype == nw.Int64()
    assert schema.fields["email"].dtype == nw.String()
    assert schema.fields["email"].nullable is True


def test_dataclass_with_metadata() -> None:
    """Test dataclass with field metadata."""

    @dataclass
    class Product:
        name: str = dc_field(metadata={"description": "Product name", "max_length": 100})
        price: float = dc_field(metadata={"min": 0, "currency": "USD"})

    schema = AnySchema(spec=Product)

    name_field = schema.fields["name"]
    assert name_field.metadata == {"description": "Product name", "max_length": 100}

    price_field = schema.fields["price"]
    assert price_field.metadata == {"min": 0, "currency": "USD"}


@pytest.mark.parametrize(
    "method_name",
    ["to_arrow", "to_polars", "to_pandas"],
)
def test_conversion_methods_still_work(method_name: str) -> None:
    """Test that conversion methods work after Field addition."""
    schema = AnySchema(spec={"id": int, "name": str, "active": bool})

    # Get the method
    method = getattr(schema, method_name)
    result = method()

    # Should not raise and should return something
    assert result is not None


def test_schema_field_count_matches() -> None:
    """Test that field count matches across different representations."""
    spec = {"id": int, "name": str, "email": Optional[str], "active": bool}
    schema = AnySchema(spec=spec)

    # Field count should match
    assert len(schema.fields) == len(spec)
    assert len(schema.to_arrow()) == len(spec)
    assert len(schema.to_polars()) == len(spec)


def test_nested_optional_with_constraints() -> None:
    """Test parsing Optional with constraints from annotated-types."""
    pipeline = make_pipeline()

    # Optional with constraints (Gt(0) makes it unsigned, Lt(100) fits in UInt8)
    field = pipeline.parse_field("score", Optional[int], (Gt(0), Lt(100)), {})

    assert field.dtype == nw.UInt8()  # Constrained to 0 < x < 100
    assert field.nullable is True  # Optional makes it nullable


def test_field_with_multiple_anyschema_metadata_keys() -> None:
    """Test field with multiple __anyschema_metadata__ keys."""
    pipeline = make_pipeline()

    field = pipeline.parse_field(
        "timestamp",
        int,
        (),
        {
            "__anyschema_metadata__": {
                "nullable": True,
                "unique": True,
                "time_zone": "UTC",
                "time_unit": "ms",
            },
            "description": "Event timestamp",
        },
    )

    # Check field properties
    assert field.nullable is True
    assert field.unique is True

    # Check that __anyschema_metadata__ is filtered from field.metadata
    assert "__anyschema_metadata__" not in field.metadata

    # But custom metadata is preserved
    assert field.metadata == {"description": "Event timestamp"}


def test_pydantic_with_nested_optional_and_constraints() -> None:
    """Test Pydantic field with Optional and constraints."""

    class User(BaseModel):
        age: Optional[int] = PydanticField(ge=0, le=150)

    schema = AnySchema(spec=User)

    age_field = schema.fields["age"]
    assert age_field.nullable is True  # Optional
    assert age_field.dtype == nw.UInt8()  # ge=0, le=150 constrains to UInt8


def test_sqlalchemy_nullable_overrides_optional_type() -> None:
    """Test that SQLAlchemy nullable setting is respected."""
    metadata_obj = MetaData()
    test_table = Table(
        "user_override",
        metadata_obj,
        Column("id", Integer, primary_key=True),
        # Explicitly set nullable=False
        Column("email", String(100), nullable=False),
        # Default nullable behavior
        Column("bio", String(500)),
    )

    schema = AnySchema(spec=test_table)

    # SQLAlchemy's nullable property should be respected
    assert schema.fields["email"].nullable is False
    assert schema.fields["bio"].nullable is True  # Default in SQLAlchemy


def test_field_from_narwhals_schema() -> None:
    """Test creating AnySchema from Narwhals Schema creates Field objects."""
    nw_schema = nw.Schema({"id": nw.Int64(), "name": nw.String()})

    schema = AnySchema(spec=nw_schema)

    # Should have fields attribute
    assert hasattr(schema, "fields")
    num_fields = 2
    assert len(schema.fields) == num_fields

    # Check field properties (default to non-nullable when creating from Schema)
    id_field = schema.fields["id"]
    assert id_field.name == "id"
    assert id_field.dtype == nw.Int64()
    assert id_field.nullable is False  # Default
    assert id_field.unique is False


def test_empty_spec_creates_empty_fields() -> None:
    """Test that empty spec creates empty fields dict."""
    schema = AnySchema(spec={})

    assert schema.fields == {}
    assert len(schema.to_arrow()) == 0


def test_field_ordering_preserved() -> None:
    """Test that field order is preserved from spec."""
    # Use OrderedDict to ensure ordering
    spec = OrderedDict([("z_field", int), ("a_field", str), ("m_field", bool)])

    schema = AnySchema(spec=spec)

    # Field order should match spec order
    field_names = list(schema.fields.keys())
    assert field_names == ["z_field", "a_field", "m_field"]


def test_description_end_to_end(pydantic_student_cls: type) -> None:
    """Test that descriptions from various sources make it to AnyField."""
    # Test Pydantic with existing fixture
    schema = AnySchema(spec=pydantic_student_cls)
    assert schema.fields["name"].description == "Student full name"
    assert schema.fields["age"].description == "Student age in years"
    assert schema.fields["date_of_birth"].description is None

    # Test SQLAlchemy
    from tests.conftest import user_table

    schema = AnySchema(spec=user_table)
    assert schema.fields["id"].description == "Primary key"
    assert schema.fields["age"].description == "User age"
    assert schema.fields["name"].description is None

    # Test dataclass
    from tests.conftest import DataclassEventWithTimeMetadata

    schema = AnySchema(spec=DataclassEventWithTimeMetadata)
    assert schema.fields["name"].description == "Event name"
    assert schema.fields["scheduled_at"].description == "Scheduled time"
    assert schema.fields["created_at"].description is None
