from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generator, TypedDict, cast

import pyarrow as pa
import pytest

from anyschema import AnySchema

if TYPE_CHECKING:
    from anyschema.typing import FieldSpec


class SimpleSchema:
    """A simple schema format for testing."""

    def __init__(self, fields: dict[str, type[Any]]) -> None:
        self.fields = fields


def simple_dict_adapter(spec: SimpleSchema) -> Generator[FieldSpec, None, None]:
    """Adapter for SimpleSchema format.

    Arguments:
        spec: A SimpleSchema instance.

    Yields:
        Tuples of (field_name, field_type, constraints, metadata).
    """
    for field_name, field_type in spec.fields.items():
        yield field_name, field_type, (), {}


class NestedSchema:
    """A schema that can contain nested schemas."""

    def __init__(self, fields: dict[str, Any]) -> None:
        self.fields = fields


def nested_adapter(spec: NestedSchema) -> Generator[FieldSpec, None, None]:
    """Adapter for nested schema structures.

    For nested schemas, we dynamically create a TypedDict so the parser
    can properly extract the field structure.

    Arguments:
        spec: A NestedSchema instance.

    Yields:
        Tuples of (field_name, field_type, constraints, metadata).
    """
    for field_name, field_value in spec.fields.items():
        if isinstance(field_value, NestedSchema):
            # For nested schemas, create a TypedDict with the proper structure
            nested_dict = {name: type_ for name, type_, *_ in nested_adapter(field_value)}
            # Create a dynamic TypedDict with the nested fields
            nested_typed_dict = TypedDict(  # type: ignore[misc]
                f"{field_name.title()}TypedDict",  # Generate a unique name
                nested_dict,  # Field name -> type mapping
            )
            yield field_name, nested_typed_dict, (), {}
        else:
            yield field_name, field_value, (), {}


def test_simple_dict_spec() -> None:
    """Test that dict types are converted to Struct."""
    fields = {"id": int, "metadata": dict}
    schema_spec = SimpleSchema(fields=fields)

    schema = AnySchema(spec=schema_spec, adapter=simple_dict_adapter)
    arrow_schema = schema.to_arrow()

    assert len(arrow_schema) == len(fields)
    assert arrow_schema.names == ["id", "metadata"]
    assert "struct" in str(arrow_schema.types[1]).lower()


def test_typed_dict_spec() -> None:
    """Test that TypedDict is converted to Struct with fields."""

    class PersonTypedDict(TypedDict):
        name: str
        age: int

    fields = {"person": PersonTypedDict}
    schema_spec = SimpleSchema(fields=fields)

    schema = AnySchema(spec=schema_spec, adapter=simple_dict_adapter)
    arrow_schema = schema.to_arrow()

    assert len(arrow_schema) == len(fields)
    assert arrow_schema.names == ["person"]
    # Should be a struct with name and age fields
    assert "struct" in str(arrow_schema.types[0]).lower()


def test_nested_schema_adapter() -> None:
    """Test the nested schema adapter from the advanced documentation."""
    fields = {
        "id": int,
        "profile": NestedSchema(
            fields={
                "name": str,
                "age": int,
            }
        ),
    }
    schema_spec = NestedSchema(fields=fields)
    schema = AnySchema(spec=schema_spec, adapter=nested_adapter)
    arrow_schema = schema.to_arrow()

    assert len(arrow_schema) == len(fields)
    assert arrow_schema.names == ["id", "profile"]
    assert "struct" in str(arrow_schema.types[1]).lower()
    # Check that the nested struct has the correct fields
    profile_type = arrow_schema.types[1]
    assert profile_type.num_fields == len(cast("NestedSchema", fields["profile"]).fields)  # Should have 2 fields
    assert pa.types.is_struct(profile_type)
    assert profile_type.names == ["name", "age"]


def test_polars_schema_with_dict() -> None:
    """Test that dict types work with Polars schema conversion."""
    fields = {"id": int, "metadata": dict, "name": str}
    schema_spec = SimpleSchema(fields=fields)

    schema = AnySchema(spec=schema_spec, adapter=simple_dict_adapter)
    polars_schema = schema.to_polars()

    assert len(polars_schema) == len(fields)
    # Polars schema items are DType classes, not instances
    assert str(polars_schema["id"]) == "Int64"
    # Polars represents empty struct as {} instead of []
    assert "Struct" in str(polars_schema["metadata"])
    assert str(polars_schema["name"]) == "String"


@pytest.mark.parametrize(
    "dict_type",
    [dict, dict[str, int], dict[str, str]],
)
def test_various_dict_types(dict_type: type) -> None:
    """Test that various dict type annotations are handled."""
    fields = {"data": dict_type}
    schema_spec = SimpleSchema(fields=fields)

    schema = AnySchema(spec=schema_spec, adapter=simple_dict_adapter)
    arrow_schema = schema.to_arrow()

    assert len(arrow_schema) == len(fields)
    assert arrow_schema.names == ["data"]
    # All dict types should become structs
    assert "struct" in str(arrow_schema.types[0]).lower()
