from __future__ import annotations

import narwhals as nw
import pytest

from anyschema import AnyField


@pytest.mark.parametrize(
    ("name", "dtype", "nullable", "unique", "metadata", "expected_nullable", "expected_unique"),
    [
        ("email", nw.String(), None, None, None, False, False),
        ("optional_field", nw.String(), True, None, None, True, False),
        ("id", nw.Int64(), False, None, None, False, False),
        ("username", nw.String(), None, True, None, False, True),
        ("code", nw.String(), True, True, None, True, True),
        ("age", nw.Int32(), None, None, {"min": 0, "max": 150}, False, False),
        ("user_id", nw.Int64(), False, True, {"description": "Primary key"}, False, True),
    ],
)
def test_field_creation_parameters(  # noqa: PLR0913
    name: str,
    dtype: nw.dtypes.DType,
    *,
    nullable: bool | None,
    unique: bool | None,
    metadata: dict[str, str] | None,
    expected_nullable: bool,
    expected_unique: bool,
) -> None:
    """Test Field creation with various parameter combinations."""
    kwargs = {"name": name, "dtype": dtype}
    if nullable is not None:
        kwargs["nullable"] = nullable
    if unique is not None:
        kwargs["unique"] = unique
    if metadata is not None:
        kwargs["metadata"] = metadata

    field = AnyField(**kwargs)  # type: ignore[arg-type]

    assert field.name == name
    assert field.dtype == dtype
    assert field.nullable is expected_nullable
    assert field.unique is expected_unique
    assert field.metadata == (metadata if metadata is not None else {})


def test_field_metadata_default_empty_dict() -> None:
    field = AnyField(name="test", dtype=nw.String())
    assert field.metadata == {}
    assert isinstance(field.metadata, dict)


def test_field_equal_fields() -> None:
    field1 = AnyField(name="id", dtype=nw.Int64(), nullable=False, unique=True, metadata={"key": "value"})
    field2 = AnyField(name="id", dtype=nw.Int64(), nullable=False, unique=True, metadata={"key": "value"})
    assert field1 == field2
    assert hash(field1) == hash(field2)


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
def test_field_unequal_fields(field1_kwargs: dict, field2_kwargs: dict) -> None:
    field1 = AnyField(**field1_kwargs)  # type: ignore[arg-type]
    field2 = AnyField(**field2_kwargs)  # type: ignore[arg-type]
    assert field1 != field2


def test_field_equality_with_non_field() -> None:
    field = AnyField(name="test", dtype=nw.String())
    assert field != "not a field"
    assert field != 42  # noqa: PLR2004
    assert field != None  # noqa: E711
    assert field != {"name": "test"}


def test_field_hashable() -> None:
    field = AnyField(name="id", dtype=nw.Int64(), nullable=False, unique=True, metadata={"key": "value"})
    assert hash(field)


def test_field_equal_fields_same_hash() -> None:
    field1 = AnyField(name="id", dtype=nw.Int64(), nullable=False, unique=True, metadata={"key": "value"})
    field2 = AnyField(name="id", dtype=nw.Int64(), nullable=False, unique=True, metadata={"key": "value"})
    assert hash(field1) == hash(field2)


def test_field_use_in_set() -> None:
    field1 = AnyField(name="id", dtype=nw.Int64())
    field2 = AnyField(name="id", dtype=nw.Int64())  # Equal to field1
    field3 = AnyField(name="name", dtype=nw.String())

    field_set = {field1, field2, field3}
    # field1 and field2 are equal, so only 2 unique items
    expected_unique_count = 2
    assert len(field_set) == expected_unique_count


def test_field_use_as_dict_key() -> None:
    """Test that Field can be used as a dictionary key."""
    field1 = AnyField(name="id", dtype=nw.Int64())
    field2 = AnyField(name="id", dtype=nw.Int64())  # Equal to field1

    field_dict = {field1: "value1"}
    field_dict[field2] = "value2"  # Should overwrite since field1 == field2

    assert len(field_dict) == 1
    assert field_dict[field1] == "value2"


@pytest.mark.parametrize(
    ("field_kwargs", "expected_parts"),
    [
        (
            {"name": "email", "dtype": nw.String()},
            ["name='email'", "dtype=String", "nullable=False", "unique=False", "description=None"],
        ),
        (
            {"name": "optional_field", "dtype": nw.String(), "nullable": True},
            ["name='optional_field'", "dtype=String", "nullable=True", "unique=False", "description=None"],
        ),
        (
            {"name": "username", "dtype": nw.String(), "unique": True},
            ["name='username'", "dtype=String", "nullable=False", "unique=True", "description=None"],
        ),
        (
            {"name": "age", "dtype": nw.Int32(), "metadata": {"min": 0}},
            ["name='age'", "dtype=Int32", "nullable=False", "unique=False", "description=None", "min"],
        ),
    ],
)
def test_field_repr_contains_expected_parts(field_kwargs: dict, expected_parts: list[str]) -> None:
    field = AnyField(**field_kwargs)  # type: ignore[arg-type]
    repr_str = repr(field)

    assert repr_str.startswith("AnyField(")
    assert repr_str.endswith(")")

    for part in expected_parts:
        assert part in repr_str, f"Expected '{part}' in repr: {repr_str}"


def test_field_repr_roundtrip_information() -> None:
    field = AnyField(
        name="score",
        dtype=nw.Float64(),
        nullable=False,
        unique=True,
        metadata={"min": 0.0, "max": 100.0},
    )
    repr_str = repr(field)

    # Should contain all critical information
    assert "score" in repr_str
    assert "Float64" in repr_str
    assert "nullable=False" in repr_str
    assert "unique=True" in repr_str
    assert "min" in repr_str
    assert "max" in repr_str


def test_field_slots_defined() -> None:
    assert hasattr(AnyField, "__slots__")


def test_field_no_dict_attribute() -> None:
    field = AnyField(name="test", dtype=nw.String())
    assert not hasattr(field, "__dict__")


def test_field_with_description() -> None:
    """Test Field creation with description."""
    field = AnyField(name="user_id", dtype=nw.Int64(), description="Unique user identifier")
    assert field.description == "Unique user identifier"


def test_field_with_none_description() -> None:
    """Test Field creation with None description."""
    field = AnyField(name="user_id", dtype=nw.Int64(), description=None)
    assert field.description is None


def test_field_description_default_none() -> None:
    """Test that description defaults to None."""
    field = AnyField(name="test", dtype=nw.String())
    assert field.description is None


def test_field_equality_with_description() -> None:
    """Test that fields with same description are equal."""
    field1 = AnyField(name="id", dtype=nw.Int64(), description="User ID")
    field2 = AnyField(name="id", dtype=nw.Int64(), description="User ID")
    assert field1 == field2
    assert hash(field1) == hash(field2)


def test_field_inequality_with_different_description() -> None:
    """Test that fields with different descriptions are not equal."""
    field1 = AnyField(name="id", dtype=nw.Int64(), description="User ID")
    field2 = AnyField(name="id", dtype=nw.Int64(), description="Product ID")
    assert field1 != field2


def test_field_inequality_with_one_none_description() -> None:
    """Test that fields with one None description are not equal."""
    field1 = AnyField(name="id", dtype=nw.Int64(), description="User ID")
    field2 = AnyField(name="id", dtype=nw.Int64(), description=None)
    assert field1 != field2
