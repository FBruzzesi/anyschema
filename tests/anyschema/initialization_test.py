from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw
import pytest
from narwhals.schema import Schema

from anyschema import AnySchema

if TYPE_CHECKING:
    from anyschema.typing import FieldSpecIterable


def test_anyschema_with_unknown_spec_and_no_adapter() -> None:
    class UnknownClass:
        """A class that doesn't match any known adapter pattern."""

        some_field: int

    expected_msg = "`spec` type is unknown and `adapter` is not specified."
    with pytest.raises(ValueError, match=expected_msg):
        AnySchema(spec=UnknownClass)


def test_anyschema_with_unknown_spec_and_custom_adapter() -> None:
    class CustomSpec:
        """A custom spec class."""

        field1: str
        field2: int

    def custom_adapter(spec: CustomSpec) -> FieldSpecIterable:  # noqa: ARG001
        yield "field1", str, (), {}
        yield "field2", int, (), {}

    schema = AnySchema(spec=CustomSpec, adapter=custom_adapter)
    result = schema.to_polars()

    assert "field1" in result
    assert "field2" in result


def test_anyschema_with_narwhals_schema() -> None:
    nw_schema = Schema({"name": nw.String(), "age": nw.Int64()})
    anyschema = AnySchema(spec=nw_schema)
    assert anyschema._nw_schema is nw_schema


def test_anyschema_with_dict_spec() -> None:
    spec = {"name": str, "age": int}

    schema = AnySchema(spec=spec)
    result = schema.to_polars()

    assert "name" in result
    assert "age" in result
