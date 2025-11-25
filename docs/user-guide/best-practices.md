# Best Practices

## For Custom Parsers

* Return `None` when you can't handle a type to let other parsers in the chain try.
* Use `self.pipeline.parse()` for recursion. This possibly allows to handle nested types by delegating to the pipeline.
* Preserve metadata: Pass metadata through when recursively parsing.
* Order matters: Place specialized parsers before general ones.
* Document what types the parser can handle: Make it clear in docstrings.

```python exec="true" source="above" session="best-practices"
from typing import Any, TypeVar, get_args, get_origin

import narwhals as nw
from anyschema.parsers import ParserStep


T = TypeVar("T")


class CustomType: ...


class CustomList[T]: ...


class GoodParserStep(ParserStep):
    """Parser for CustomType.

    Handles:

    - CustomType: converts to String
    - CustomList[T]: converts to List(T)
    """

    def parse(self, input_type: Any, metadata: tuple = ()) -> nw.dtypes.DType | None:
        # Check if we can handle this type
        if input_type is CustomType:
            return nw.String()

        # Handle generic version
        if get_origin(input_type) is CustomList:
            inner = get_args(input_type)[0]
            # Delegate to pipeline for recursion
            inner_dtype = self.pipeline.parse(inner, metadata=metadata)
            return nw.List(inner_dtype)

        # Return None if we can't handle it
        return None
```

## For Custom Adapters

* Use generators: Yield instead of returning a list for memory efficiency.
* Handle nested structures: Recursively convert nested schemas.
* Validate input: Check that the spec is the expected format.
* Convert metadata consistently: Have a clear mapping from your format to anyschema metadata.
* Document the expected input format: Make it clear what spec format you accept.

```python exec="true" source="above" session="best-practices"
from typing import Any, TypedDict
from anyschema.typing import FieldSpecIterable


class CustomSchemaSpec:
    def __init__(self, fields: dict[str, Any]) -> None:
        self.fields = fields


def good_adapter(spec: CustomSchemaSpec) -> FieldSpecIterable:
    """Adapter for CustomSchemaSpec structures.

    For nested schemas, we dynamically create a TypedDict so the parser
    can properly extract the field structure.

    Arguments:
        spec: A CustomSchemaSpec instance.

    Yields:
        Tuples of (field_name, field_type, metadata).

    Raises:
        TypeError: If spec is not a CustomSchemaSpec instance.
    """
    if not isinstance(spec, CustomSchemaSpec):
        raise TypeError(f"Expected `CustomSchemaSpec`, got {type(spec)}")

    for field_name, field_value in spec.fields.items():
        if isinstance(field_value, CustomSchemaSpec):
            # For nested schemas, create a TypedDict with the proper structure
            nested_dict = {name: type_ for name, type_, _ in good_adapter(field_value)}
            # Create a dynamic TypedDict with the nested fields
            nested_typed_dict = TypedDict(
                f"{field_name.title()}TypedDict",
                nested_dict,
            )
            yield field_name, nested_typed_dict, ()
        else:
            yield field_name, field_value, ()
```

## Integration Testing

Test your custom components thoroughly at multiple levels: unit tests for individual parsers and adapters, and
integration tests for the complete flow.

```python exec="true" source="above" session="best-practices"
import polars as pl
import pytest

from anyschema import AnySchema
from anyschema.parsers import make_pipeline, ParserPipeline, PyTypeStep


@pytest.fixture(scope="module")
def custom_step() -> GoodParserStep:
    custom_step = GoodParserStep()
    python_step = PyTypeStep()
    _ = make_pipeline([custom_step, python_step])
    return custom_step


@pytest.mark.parametrize(
    ("input_type", "expected_dtype"),
    [
        (CustomType, nw.String()),
        (CustomList[int], nw.List(nw.Int64())),
        (str, None),
    ],
)
def test_custom_step_parse(
    custom_step: GoodParserStep, input_type: Any, expected_dtype: nw.dtypes.DType
) -> None:
    """Test that custom parser handles its types correctly."""
    result = custom_step.parse(CustomType)
    assert result == expected_dtype


def test_custom_adapter() -> None:
    """Test that custom adapter converts spec correctly."""
    fields = {
        "id": int,
        "name": str,
    }
    spec = CustomSchemaSpec(fields)
    result = list(good_adapter(spec))

    assert len(result) == len(fields)

    expected = [
        ("id", int, ()),
        ("name", str, ()),
    ]
    assert result == expected


def test_custom_adapter_nested() -> None:
    """Test that custom adapter handles nested schemas."""
    inner_fields = {
        "name": str,
        "age": int,
    }
    fields = {
        "id": int,
        "profile": CustomSchemaSpec(fields=inner_fields),
    }
    spec = CustomSchemaSpec(fields=fields)
    result = list(good_adapter(spec))

    assert len(result) == len(fields)
    assert result[0] == ("id", int, ())

    # Check that nested field is a TypedDict
    assert result[1][0] == "profile"
    assert hasattr(result[1][1], "__annotations__")


def test_custom_components_integration():
    """Test custom parser and adapter working together end-to-end."""
    schema_spec = CustomSchemaSpec(
        fields={
            "custom_field": CustomType,
            "custom_list": CustomList[int],
            "name": str,
        }
    )

    schema = AnySchema(
        spec=schema_spec,
        steps=[GoodParserStep(), PyTypeStep()],
        adapter=good_adapter,
    )

    # Verify the conversion to Arrow works correctly
    scehma_pa = schema.to_arrow()
    assert scehma_pa.names == ["custom_field", "custom_list", "name"]

    # Verify types are converted correctly
    schema_pl = schema.to_polars()
    expected_pl = pl.Schema(
        {
            "custom_field": pl.String(),
            "custom_list": pl.List(pl.Int64()),
            "name": pl.String(),
        },
    )
    assert schema_pl == expected_pl
```
