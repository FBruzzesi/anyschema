from __future__ import annotations

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


@pytest.mark.parametrize("nullable", [True, False])
def test_parse_field_nullable_metadata(*, nullable: bool) -> None:
    pipeline = make_pipeline()
    field = pipeline.parse_field("test", int, (), {"anyschema/nullable": nullable})

    assert field.nullable is nullable


def test_parse_field_nullable_metadata_overwrite() -> None:
    # !NOTE: Test that explicit nullable=False overrides Optional type
    pipeline = make_pipeline()

    field = pipeline.parse_field("test-optional", Optional[str], (), {"anyschema/nullable": False})
    assert field == AnyField(name="test-optional", dtype=nw.String(), nullable=False)

    field = pipeline.parse_field("test-required", str, (), {"anyschema/nullable": True})
    assert field == AnyField(name="test-required", dtype=nw.String(), nullable=True)


@pytest.mark.parametrize("unique", [True, False])
def test_parse_field_unique(*, unique: bool) -> None:
    pipeline = make_pipeline()
    field = pipeline.parse_field("test", str, (), {"anyschema/unique": unique})

    assert field.unique is unique


def test_anyschema_metadata_filtered_from_field_metadata() -> None:
    """Test that anyschema/* keys are filtered from Field.metadata."""
    pipeline = make_pipeline()
    field = pipeline.parse_field(
        "test",
        int,
        (),
        {
            "anyschema/nullable": False,
            "anyschema/unique": True,
            "anyschema/time_zone": "UTC",
            "description": "A test field",
            "custom_key": "custom_value",
        },
    )
    assert field.unique is True

    # anyschema/* keys should not be in field.metadata
    assert all(not k.startswith("anyschema/") for k in field.metadata)

    # Custom metadata should be preserved
    assert field.metadata == {"description": "A test field", "custom_key": "custom_value"}


@pytest.mark.parametrize(
    "spec",
    [
        {"id": int},
        {"id": int, "name": str},
        {"id": int, "name": str, "age": int, "active": bool},
    ],
)
def test_anyschema_fields_contains_all_spec_fields(spec: dict[str, type]) -> None:
    """Test that all fields from spec are in the fields attribute."""
    schema = AnySchema(spec=spec)
    result_fields = schema.fields
    expected_fields = tuple(spec.keys())

    assert result_fields.keys() == spec.keys()
    assert all(isinstance(field, AnyField) for field in result_fields.values())
    assert len(schema.fields) == len(expected_fields)


def test_pydantic_student_fields_presence(pydantic_student_cls: type[BaseModel]) -> None:
    """Test that expected fields are present in PydanticStudent fixture."""
    schema = AnySchema(spec=pydantic_student_cls)
    expected = ("name", "date_of_birth", "age", "classes", "has_graduated")

    assert tuple(schema.fields.keys()) == expected


def test_pydantic_student_field_properties(pydantic_student_cls: type[BaseModel]) -> None:
    """Test field properties of PydanticStudent fixture."""
    schema = AnySchema(spec=pydantic_student_cls)
    expected = (
        ("name", nw.String(), False),
        ("age", nw.UInt64(), False),
    )
    for name, dtype, nullable in expected:
        field = schema.fields[name]
        assert field.dtype == dtype
        assert field.nullable is nullable


def test_pydantic_with_explicit_metadata() -> None:
    """Test Pydantic model with explicit nullable and unique metadata."""

    class UserWithMetadata(BaseModel):
        id: int = PydanticField(json_schema_extra={"anyschema/nullable": False, "anyschema/unique": True})
        username: str = PydanticField(json_schema_extra={"anyschema/unique": True, "description": "User's login name"})
        email: Optional[str] = PydanticField(json_schema_extra={"format": "email"})

    schema = AnySchema(spec=UserWithMetadata)
    expected = (
        ("id", False, True, {}),
        ("username", False, True, {"description": "User's login name"}),
        ("email", True, False, {"format": "email"}),
    )
    for name, nullable, unique, metadata in expected:
        field = schema.fields[name]

        assert field.nullable is nullable
        assert field.unique is unique
        assert field.metadata == metadata
        # anyschema/* keys should be filtered
        assert all(not k.startswith("anyschema/") for k in field.metadata)


def test_pydantic_with_custom_metadata() -> None:
    """Test that custom metadata from Pydantic is preserved."""

    class ProductWithMetadata(BaseModel):
        name: str = PydanticField(json_schema_extra={"max_length": 100, "description": "Product name"})
        price: float = PydanticField(json_schema_extra={"min": 0, "currency": "USD"})

    schema = AnySchema(spec=ProductWithMetadata)

    expected = (
        ("name", {"max_length": 100, "description": "Product name"}),
        ("price", {"min": 0, "currency": "USD"}),
    )
    for name, metadata in expected:
        assert schema.fields[name].metadata == metadata


def test_sqlalchemy_user_table() -> None:
    """Test parsing user_table from conftest."""
    schema = AnySchema(spec=user_table)
    expected = (
        ("id", nw.Int32(), False),  # primary_key, not nullable
        ("email", nw.String(), True),  # explicitly nullable
    )
    for name, dtype, nullable in expected:
        field = schema.fields[name]
        assert field.nullable is nullable
        assert field.dtype == dtype


def test_sqlalchemy_auto_detects_nullable() -> None:
    """Test that SQLAlchemy nullable property is auto-detected."""
    metadata = MetaData()
    test_table = Table(
        "test",
        metadata,
        Column("not_null", Integer, nullable=False),
        Column("nullable", Integer, nullable=True),
        Column("default_nullable", Integer),
    )
    schema = AnySchema(spec=test_table)

    expected = (
        ("not_null", False),
        ("nullable", True),
        ("default_nullable", True),  # Default is nullable
    )
    for field_name, nullable in expected:
        assert schema.fields[field_name].nullable is nullable


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

    expected = (
        ("id", False),  # primary_key doesn't set unique in our implementation
        ("unique_username", True),
        ("normal_field", False),
    )
    for field_name, unique in expected:
        assert schema.fields[field_name].unique is unique


def test_attrs_person() -> None:
    """Test parsing AttrsPerson fixture."""
    schema = AnySchema(spec=AttrsPerson)
    expected = (
        ("name", nw.String()),
        ("age", nw.Int64()),
        ("date_of_birth", nw.Date()),
        ("is_active", nw.Boolean()),
    )
    for name, dtype in expected:
        field = schema.fields[name]
        assert field.dtype == dtype


def test_attrs_with_metadata() -> None:
    """Test attrs class with metadata."""
    schema = AnySchema(spec=AttrsBookWithMetadata)
    expected = (
        ("title", {"description": "Book title"}),
        ("author", {"max_length": 100}),
    )
    for name, metadata in expected:
        field = schema.fields[name]
        assert field.metadata == metadata


def test_dataclass_basic() -> None:
    """Test parsing basic dataclass."""

    @dataclass
    class Person:
        name: str
        age: int
        email: Optional[str]

    schema = AnySchema(spec=Person)

    expected = (
        ("name", nw.String(), False),
        ("age", nw.Int64(), False),
        ("email", nw.String(), True),
    )
    assert len(schema.fields) == len(expected)

    for name, dtype, nullable in expected:
        field = schema.fields[name]
        assert field.dtype == dtype
        assert field.nullable is nullable


def test_dataclass_with_metadata() -> None:
    """Test dataclass with field metadata."""

    @dataclass
    class Product:
        name: str = dc_field(metadata={"description": "Product name", "max_length": 100})
        price: float = dc_field(metadata={"min": 0, "currency": "USD"})

    schema = AnySchema(spec=Product)

    expected = (
        ("name", {"description": "Product name", "max_length": 100}),
        ("price", {"min": 0, "currency": "USD"}),
    )

    for name, meta in expected:
        field = schema.fields[name]
        assert field.metadata == meta


def test_nested_optional_with_constraints() -> None:
    """Test parsing Optional with constraints from annotated-types."""
    pipeline = make_pipeline()

    # Optional with constraints (Gt(0) makes it unsigned, Lt(100) fits in UInt8)
    field = pipeline.parse_field("score", Optional[int], (Gt(0), Lt(100)), {})

    assert field.dtype == nw.UInt8()  # Constrained to 0 < x < 100
    assert field.nullable is True  # Optional makes it nullable
