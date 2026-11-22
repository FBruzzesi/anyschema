from __future__ import annotations

import sys
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import TYPE_CHECKING, Annotated, Any, ForwardRef, Literal, Optional, Union

import narwhals as nw
import pytest
from annotated_types import Gt, Lt
from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import Column, Integer, MetaData, String, Table

from anyschema import AnyField, AnySchema
from anyschema._metadata import set_anyschema_meta
from anyschema.parsers import ForwardRefStep, ParserStep, PyTypeStep, UnionTypeStep, make_pipeline
from anyschema.serde import serialize_dtype
from tests.conftest import AttrsBookWithMetadata, AttrsPerson, user_table

if TYPE_CHECKING:
    from collections.abc import Iterable

    from narwhals.dtypes import DType

    from anyschema.typing import AnySchemaMetadata, AnySchemaNamespaceKey, FieldConstraints, FieldMetadata, FieldType


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
def test_parse_into_field(name: str, py_type: type, expected_dtype: nw.dtypes.DType) -> None:
    pipeline = make_pipeline()
    field = pipeline.parse_into_field(name, py_type, (), {})

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
def test_parse_into_field_nullable_type(name: str, py_type: type, expected_dtype: nw.dtypes.DType) -> None:
    pipeline = make_pipeline()
    field = pipeline.parse_into_field(name, py_type, (), {})

    assert field == AnyField(name=name, dtype=expected_dtype, nullable=True)


@pytest.mark.parametrize("nullable", [True, False])
def test_parse_into_field_nullable_metadata(*, nullable: bool) -> None:
    pipeline = make_pipeline()
    field = pipeline.parse_into_field("test", int, (), {"anyschema": {"nullable": nullable}})

    assert field.nullable is nullable


def test_parse_into_field_nullable_metadata_overwrite() -> None:
    # !NOTE: Test that explicit nullable=False overrides Optional type
    pipeline = make_pipeline()

    field = pipeline.parse_into_field("test-optional", Optional[str], (), {"anyschema": {"nullable": False}})
    assert field == AnyField(name="test-optional", dtype=nw.String(), nullable=False)

    field = pipeline.parse_into_field("test-required", str, (), {"anyschema": {"nullable": True}})
    assert field == AnyField(name="test-required", dtype=nw.String(), nullable=True)


@pytest.mark.parametrize("unique", [True, False])
def test_parse_into_field_unique(*, unique: bool) -> None:
    pipeline = make_pipeline()
    field = pipeline.parse_into_field("test", str, (), {"anyschema": {"unique": unique}})

    assert field.unique is unique


@pytest.mark.parametrize("unique", [True, False])
def test_parse_into_field_unique_with_x_prefix(*, unique: bool) -> None:
    """Test that x-anyschema prefix works (OpenAPI compatibility)."""
    pipeline = make_pipeline()
    field = pipeline.parse_into_field("test", str, (), {"x-anyschema": {"unique": unique}})

    assert field.unique is unique


def test_anyschema_metadata_filtered_from_field_metadata() -> None:
    """Test that anyschema and x-anyschema keys are filtered from Field.metadata."""
    pipeline = make_pipeline()
    field = pipeline.parse_into_field(
        "test",
        int,
        (),
        {
            "anyschema": {
                "nullable": False,
                "unique": True,
                "time_zone": "UTC",
                "description": "A test field",
            },
            "custom_key": "custom_value",
        },
    )
    assert field.unique is True

    # anyschema and x-anyschema keys should not be in field.metadata
    assert "anyschema" not in field.metadata
    assert "x-anyschema" not in field.metadata

    # Custom metadata should be preserved
    assert field.metadata == {"custom_key": "custom_value"}


def test_x_anyschema_metadata_filtered_from_field_metadata() -> None:
    """Test that x-anyschema prefix works and is filtered from Field.metadata."""
    pipeline = make_pipeline()
    field = pipeline.parse_into_field(
        "test",
        int,
        (),
        {
            "x-anyschema": {
                "nullable": False,
                "unique": True,
                "description": "A test field with x-prefix",
            },
            "custom_key": "custom_value",
        },
    )
    assert field.unique is True
    assert field.nullable is False
    assert field.description == "A test field with x-prefix"

    # Both anyschema and x-anyschema keys should not be in field.metadata
    assert "anyschema" not in field.metadata
    assert "x-anyschema" not in field.metadata

    # Custom metadata should be preserved
    assert field.metadata == {"custom_key": "custom_value"}


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


def test_pydantic_student_fields(pydantic_student_cls: type[BaseModel]) -> None:
    """Test PydanticStudent fixture field presence and properties."""
    schema = AnySchema(spec=pydantic_student_cls)

    # Check all expected fields are present in order
    expected_fields = ("name", "date_of_birth", "age", "classes", "has_graduated")
    assert tuple(schema.fields.keys()) == expected_fields

    # Check specific field properties
    assert schema.fields["name"].dtype == nw.String()
    assert schema.fields["name"].nullable is False

    assert schema.fields["age"].dtype == nw.UInt64()
    assert schema.fields["age"].nullable is False


def test_pydantic_with_explicit_metadata() -> None:
    """Test Pydantic model with explicit nullable and unique metadata."""

    class UserWithMetadata(BaseModel):
        id: int = PydanticField(json_schema_extra={"anyschema": {"nullable": False, "unique": True}})
        username: str = PydanticField(
            json_schema_extra={
                "anyschema": {"unique": True},
                "description": "User's login name",  # description outside anyschema namespace
            }
        )
        email: Optional[str] = PydanticField(json_schema_extra={"format": "email"})

    schema = AnySchema(spec=UserWithMetadata)
    expected: Iterable[tuple[str, bool, bool, dict[str, Any]]] = (
        ("id", False, True, {}),
        ("username", False, True, {"description": "User's login name"}),
        ("email", True, False, {"format": "email"}),
    )
    for name, nullable, unique, metadata in expected:
        field = schema.fields[name]

        assert field.nullable is nullable
        assert field.unique is unique
        assert field.metadata == metadata
        # anyschema* keys should be filtered
        assert all(not k.startswith("anyschema") for k in field.metadata)


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
    """Test parsing user_table fixture from conftest."""
    schema = AnySchema(spec=user_table)

    # Check specific fields with dtype and nullable
    assert schema.fields["id"].dtype == nw.Int32()
    assert schema.fields["id"].nullable is False  # primary_key

    assert schema.fields["email"].dtype == nw.String()
    assert schema.fields["email"].nullable is True  # explicitly nullable


def test_sqlalchemy_auto_detects_nullable_and_unique() -> None:
    """Test that SQLAlchemy nullable and unique properties are auto-detected."""
    metadata = MetaData()
    test_table = Table(
        "test",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("unique_username", String(50), unique=True, nullable=False),
        Column("nullable_field", Integer, nullable=True),
        Column("normal_field", String(50)),
    )

    schema = AnySchema(spec=test_table)

    expected = (
        ("id", False, False),  # primary_key sets nullable=False, but not unique in our implementation
        ("unique_username", False, True),
        ("nullable_field", True, False),
        ("normal_field", True, False),  # Default is nullable, not unique
    )
    for field_name, nullable, unique in expected:
        field = schema.fields[field_name]
        assert field.nullable is nullable
        assert field.unique is unique


def test_attrs_person_fields() -> None:
    """Test parsing AttrsPerson fixture fields and types."""
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


def test_attrs_book_with_metadata() -> None:
    """Test attrs class with field metadata."""
    schema = AnySchema(spec=AttrsBookWithMetadata)
    expected = (
        ("title", {"description": "Book title"}),
        ("author", {"max_length": 100}),
    )
    for name, metadata in expected:
        field = schema.fields[name]
        assert field.metadata == metadata


def test_dataclass_fields_and_metadata() -> None:
    """Test parsing dataclass with basic fields and metadata."""

    @dataclass
    class Person:
        name: str
        age: int
        email: Optional[str]

    schema = AnySchema(spec=Person)

    # Check basic field types and nullable
    expected_basic = (
        ("name", nw.String(), False),
        ("age", nw.Int64(), False),
        ("email", nw.String(), True),
    )
    assert len(schema.fields) == len(expected_basic)

    for name, dtype, nullable in expected_basic:
        field = schema.fields[name]
        assert field.dtype == dtype
        assert field.nullable is nullable

    # Check metadata in a separate dataclass
    @dataclass
    class Product:
        name: str = dc_field(metadata={"description": "Product name", "max_length": 100})
        price: float = dc_field(metadata={"min": 0, "currency": "USD"})

    schema_product = AnySchema(spec=Product)

    expected_metadata = (
        ("name", {"description": "Product name", "max_length": 100}),
        ("price", {"min": 0, "currency": "USD"}),
    )

    for name, meta in expected_metadata:
        field = schema_product.fields[name]
        assert field.metadata == meta


def test_nested_optional_with_constraints() -> None:
    """Test parsing Optional with constraints from annotated-types."""
    pipeline = make_pipeline()

    # Optional with constraints (Gt(0) makes it unsigned, Lt(100) fits in UInt8)
    field = pipeline.parse_into_field("score", Optional[int], (Gt(0), Lt(100)), {})

    assert field.dtype == nw.UInt8()  # Constrained to 0 < x < 100
    assert field.nullable is True  # Optional makes it nullable


@pytest.mark.parametrize("namespace", ["anyschema", "x-anyschema"])
@pytest.mark.parametrize(
    "dtype", [nw.String(), nw.Int32(), nw.List(nw.Float64()), nw.Datetime(time_unit="ms", time_zone="UTC")]
)
def test_parse_into_field_dtype_override_with_narwhals_dtype(namespace: AnySchemaNamespaceKey, dtype: DType) -> None:
    pipeline = make_pipeline()

    field = pipeline.parse_into_field("test", int, (), {namespace: {"dtype": dtype}})
    assert field.dtype == dtype


@pytest.mark.parametrize("namespace", ["anyschema", "x-anyschema"])
@pytest.mark.parametrize(
    "dtype", [nw.String(), nw.Int32(), nw.List(nw.Float64()), nw.Datetime(time_unit="ms", time_zone="UTC")]
)
def test_parse_into_field_dtype_override_with_string(namespace: AnySchemaNamespaceKey, dtype: DType) -> None:
    pipeline = make_pipeline()

    field = pipeline.parse_into_field("test", int, (), {namespace: {"dtype": serialize_dtype(dtype)}})
    assert field.dtype == dtype


def test_parse_into_field_dtype_override_with_nullable() -> None:
    pipeline = make_pipeline()

    # Override dtype and set nullable
    field = pipeline.parse_into_field(
        "test", int, (), {"anyschema": {"dtype": nw.String(), "nullable": True, "unique": True}}
    )
    assert field.dtype == nw.String()
    assert field.nullable is True
    assert field.unique is True


class MaybeInt:
    """A user type that a custom step parses as `int | None`."""


class MaybeIntStep(ParserStep):
    """Parses `MaybeInt` as `int | None`, and writes `nullable` into the metadata unless it is `None`."""

    def __init__(self, *, nullable: bool | None) -> None:
        self.nullable = nullable

    def parse(self, input_type: FieldType, constraints: FieldConstraints, metadata: FieldMetadata) -> DType | None:
        if input_type is not MaybeInt:
            return None
        if self.nullable is not None:
            set_anyschema_meta(metadata, key="nullable", value=self.nullable)
        return self.pipeline.parse(Optional[int], constraints, metadata, strict=True)


@pytest.mark.parametrize(
    ("py_type", "step_nullable", "expected_nullable"),
    [
        (MaybeInt, None, False),  # The step's `int | None` is not at the field level
        (MaybeInt, True, True),
        (Optional[MaybeInt], None, True),
        (Optional[MaybeInt], False, False),  # A value the step writes beats the field-level `| None`
    ],
)
def test_parse_into_field_custom_step_nullable(
    py_type: Any, *, step_nullable: bool | None, expected_nullable: bool
) -> None:
    pipeline = make_pipeline([MaybeIntStep(nullable=step_nullable), UnionTypeStep(), PyTypeStep()])
    field = pipeline.parse_into_field("x", py_type, (), {})
    assert field == AnyField(name="x", dtype=nw.Int64(), nullable=expected_nullable)


def test_parse_into_field_custom_step_write_does_not_leak_into_shared_metadata() -> None:
    shared: dict[str, Any] = {"anyschema": {"unique": True}}
    pipeline = make_pipeline([MaybeIntStep(nullable=True), UnionTypeStep(), PyTypeStep()])

    maybe = pipeline.parse_into_field("maybe", MaybeInt, (), shared)
    other = pipeline.parse_into_field("other", int, (), shared)

    assert maybe.nullable is True
    assert other.nullable is False
    assert shared == {"anyschema": {"unique": True}}


def test_parse_into_field_optional_string_annotation_without_forward_ref_step_is_nullable() -> None:
    pipeline = make_pipeline([UnionTypeStep(), PyTypeStep()])
    field = pipeline.parse_into_field("x", Optional["int"], (), {"anyschema": {"dtype": "Int32"}})
    assert field == AnyField(name="x", dtype=nw.Int32(), nullable=True)


@pytest.mark.parametrize(
    ("py_type", "anyschema_meta", "expected_dtype", "expected_nullable"),
    [
        # Field-level `None`
        (int | None, {}, nw.Int64(), True),
        (Optional[int], {}, nw.Int64(), True),
        (Annotated[Optional[int], "x"], {}, nw.Int64(), True),
        (Optional[Annotated[int, "x"]], {}, nw.Int64(), True),
        (ForwardRef("int | None"), {}, nw.Int64(), True),
        (Annotated["int | None", "meta"], {}, nw.Int64(), True),
        (Annotated["Optional[int]", Gt(0)], {}, nw.UInt64(), True),
        (Optional["int"], {}, nw.Int64(), True),
        (Literal["a", None], {}, nw.Enum(["a"]), True),  # noqa: PYI061
        (Annotated[Literal["a", None], "x"], {}, nw.Enum(["a"]), True),  # noqa: PYI061
        (Literal["a", "b"], {}, nw.Enum(["a", "b"]), False),
        # Nested `None`: only the elements are nullable
        (list[Optional[int]], {}, nw.List(nw.Int64()), False),
        (tuple[Optional[int], ...], {}, nw.List(nw.Int64()), False),
        (tuple[Optional[int], Optional[int]], {}, nw.Array(nw.Int64(), 2), False),
        (list[list[Optional[int]]], {}, nw.List(nw.List(nw.Int64())), False),
        (list[Literal["a", None]], {}, nw.List(nw.Enum(["a"])), False),  # noqa: PYI061
        (Optional[list[Optional[int]]], {}, nw.List(nw.Int64()), True),
        # `dtype` override
        (Optional[int], {"dtype": "Float32"}, nw.Float32(), True),
        (ForwardRef("int | None"), {"dtype": "Int32"}, nw.Int32(), True),
        (Union[int, str, None], {"dtype": "String"}, nw.String(), True),
        (Union[int, str], {"dtype": "String"}, nw.String(), False),
        (Literal["a", None], {"dtype": "String"}, nw.String(), True),  # noqa: PYI061
        # Explicit `nullable` wins, `None` counts as unset
        (Optional[int], {"nullable": False}, nw.Int64(), False),
        (Optional[int], {"nullable": None}, nw.Int64(), True),
        (int, {"nullable": None}, nw.Int64(), False),
        (Literal["a", None], {"nullable": False}, nw.Enum(["a"]), False),  # noqa: PYI061
        (Optional[int], {"dtype": "Float32", "nullable": True}, nw.Float32(), True),
        (Optional[int], {"dtype": "Float32", "nullable": False}, nw.Float32(), False),
        (Optional[int], {"dtype": "Float32", "nullable": None}, nw.Float32(), True),
    ],
)
def test_parse_into_field_nullable(
    py_type: Any, anyschema_meta: AnySchemaMetadata, expected_dtype: DType, *, expected_nullable: bool
) -> None:
    field = make_pipeline().parse_into_field("x", py_type, (), {"anyschema": anyschema_meta})
    assert field == AnyField(name="x", dtype=expected_dtype, nullable=expected_nullable)


@pytest.mark.parametrize(
    ("forward_ref", "with_forward_ref_step"),
    [(ForwardRef("Missing | None"), True), (ForwardRef("int | None"), False)],
)
def test_parse_into_field_unresolved_forward_ref_with_dtype_override_is_not_nullable(
    forward_ref: ForwardRef, *, with_forward_ref_step: bool
) -> None:
    # Known limit: the `None` of a forward ref that is not resolved is not seen. Set `nullable` explicitly.
    steps = [UnionTypeStep(), PyTypeStep()]
    pipeline = make_pipeline([ForwardRefStep(), *steps] if with_forward_ref_step else steps)
    field = pipeline.parse_into_field("x", forward_ref, (), {"anyschema": {"dtype": "Int32"}})
    assert field == AnyField(name="x", dtype=nw.Int32(), nullable=False)


@pytest.mark.skipif(sys.version_info < (3, 14), reason="`ForwardRef` parses its string eagerly before Python 3.14")
def test_parse_into_field_malformed_forward_ref_with_dtype_override_is_not_nullable() -> None:
    field = make_pipeline().parse_into_field("x", ForwardRef("int |"), (), {"anyschema": {"dtype": "Int32"}})
    assert field == AnyField(name="x", dtype=nw.Int32(), nullable=False)


def test_anyschema_nullables_field_level_only() -> None:
    class Model(BaseModel):
        a: Optional[int] = PydanticField(json_schema_extra={"anyschema": {"dtype": "Int32"}})
        b: list[Optional[int]]
        c: list[Literal["a", None]]  # noqa: PYI061

    assert AnySchema(spec=Model).nullables() == (True, False, False)


@pytest.mark.parametrize(
    "dtype", [123, 3.14, b"foo", True, ["a", "python", "list"], ("here", "a", "tuple"), {"a": "dict"}]
)
def test_parse_into_field_dtype_override_invalid_type_raises(dtype: Any) -> None:
    pipeline = make_pipeline()

    with pytest.raises(TypeError, match="Expected `dtype` value to be of type"):
        pipeline.parse_into_field("test", int, (), {"anyschema": {"dtype": dtype}})
