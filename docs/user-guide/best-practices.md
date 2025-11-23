
## Best Practices

### For Custom Parsers

1. **Return None when you can't handle a type**: Let other parsers in the chain try
2. **Use `self.pipeline.parse()` for recursion**: Handle nested types by delegating to the pipeline
3. **Preserve metadata**: Pass metadata through when recursively parsing
4. **Order matters**: Place specialized parsers before general ones
5. **Handle errors gracefully**: Return None instead of raising exceptions when possible
6. **Document what types you handle**: Make it clear in docstrings

```python
class GoodParserStep(ParserStep):
    """Parser for CustomType.

    Handles:
    - CustomType: converts to String
    - CustomList[T]: converts to List(T)
    """

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
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

### For Custom Adapters

1. **Use generators**: Yield instead of returning a list for memory efficiency
2. **Preserve field order**: Use OrderedDict if needed
3. **Handle nested structures**: Recursively convert nested schemas
4. **Validate input**: Check that the spec is the expected format
5. **Convert metadata consistently**: Have a clear mapping from your format to anyschema metadata
6. **Document the expected input format**: Make it clear what spec format you accept

```python
def good_adapter(spec: MySchemaType) -> Iterator[tuple[str, type, tuple]]:
    """Adapter for MySchemaType.

    Arguments:
        spec: A MySchemaType instance with fields attribute.

    Yields:
        Tuples of (field_name, field_type, metadata).

    Raises:
        TypeError: If spec is not a MySchemaType instance.
    """
    if not isinstance(spec, MySchemaType):
        raise TypeError(f"Expected MySchemaType, got {type(spec)}")

    for field in spec.fields:
        # Convert your metadata format to anyschema format
        metadata = tuple(field.get("constraints", []))
        yield field.name, field.type, metadata
```

## Testing Custom Components

### Testing Custom Parsers

```python
import pytest
from anyschema.parsers import ParserPipeline, PyTypeStep


def test_color_step():
    """Test that ColorStep handles Color types."""
    color_step = ColorStep()
    python_step = PyTypeStep()
    pipeline = ParserPipeline([color_step, python_step])

    color_step.pipeline = pipeline
    python_step.pipeline = pipeline

    # Test that it handles Color
    result = color_step.parse(Color)
    assert result == nw.String()

    # Test that it ignores other types
    result = color_step.parse(int)
    assert result is None
```

### Testing Custom Adapters

```python
def test_simple_schema_adapter():
    """Test that simple_schema_adapter works correctly."""
    spec = SimpleSchema(
        fields=[
            {"name": "id", "type": int},
            {"name": "name", "type": str},
        ]
    )

    result = list(simple_schema_adapter(spec))

    assert len(result) == 2
    assert result[0] == ("id", int, ())
    assert result[1] == ("name", str, ())
```

### Integration Testing

```python
def test_custom_components_integration():
    """Test custom parser and adapter together."""
    # Create schema with custom components
    schema_spec = SimpleSchema(
        fields=[
            {"name": "color", "type": Color},
            {"name": "name", "type": str},
        ]
    )

    schema = AnySchema(
        spec=schema_spec,
        steps=[ColorStep(), PyTypeStep()],
        adapter=simple_schema_adapter,
    )

    # Verify the conversion works
    arrow_schema = schema.to_arrow()
    assert "color" in arrow_schema.names
    assert "name" in arrow_schema.names
```

## Real-World Example: JSON Schema Adapter

Here's a practical example of adapting from JSON Schema:

```python
from typing import Iterator, Any
from anyschema import AnySchema


def json_schema_adapter(spec: dict) -> Iterator[tuple[str, type, tuple]]:
    """Adapter for JSON Schema format.

    Arguments:
        spec: A JSON Schema dict with "type": "object" and "properties".

    Yields:
        Tuples of (field_name, field_type, metadata).
    """
    if spec.get("type") != "object":
        raise ValueError("Only object types supported")

    properties = spec.get("properties", {})
    required = set(spec.get("required", []))

    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    for field_name, field_spec in properties.items():
        json_type = field_spec.get("type")
        python_type = type_mapping.get(json_type, object)

        # Handle optional fields
        if field_name not in required:
            python_type = python_type | None

        # Handle array types
        if json_type == "array" and "items" in field_spec:
            item_type = type_mapping.get(field_spec["items"].get("type"), object)
            python_type = list[item_type]

        yield field_name, python_type, ()


# Usage
json_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "email": {"type": "string"},
    },
    "required": ["id", "name"],
}

schema = AnySchema(spec=json_schema, adapter=json_schema_adapter)
print(schema.to_arrow())
```





---


## Complete Custom Example

Here's a complete example combining custom parsers, adapters, and business logic:

```python
from typing import Any, Iterator
from narwhals.dtypes import DType
import narwhals as nw
from anyschema import AnySchema
from anyschema.parsers import (
    ParserStep,
    ParserPipeline,
    ForwardRefStep,
    UnionTypeStep,
    AnnotatedStep,
    PyTypeStep,
)


# 1. Define custom business types
class Email:
    """Email address type."""

    pass


class PhoneNumber:
    """Phone number type."""

    pass


class Currency:
    """Monetary value type."""

    pass


# 2. Create custom parser for business types
class BusinessTypeStep(ParserStep):
    """Parser for custom business types."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        if input_type is Email:
            return nw.String()
        elif input_type is PhoneNumber:
            return nw.String()
        elif input_type is Currency:
            return nw.Decimal()
        return None


# 3. Define custom schema format
class BusinessSchema:
    """Custom schema format for business applications."""

    def __init__(self, entity_name: str, fields: list[dict]):
        self.entity_name = entity_name
        self.fields = fields


# 4. Create adapter for the custom format
def business_schema_adapter(spec: BusinessSchema) -> Iterator[tuple[str, type, tuple]]:
    """Adapter for BusinessSchema format."""
    for field in spec.fields:
        field_name = field["name"]
        field_type = field["type"]
        required = field.get("required", True)

        # Convert required=False to Optional
        if not required:
            field_type = field_type | None

        yield field_name, field_type, ()


# 5. Create pipeline with custom parser
forward_ref_step = ForwardRefStep()
union_step = UnionTypeStep()
annotated_step = AnnotatedStep()
business_step = BusinessTypeStep()
python_step = PyTypeStep()

pipeline = ParserPipeline(
    steps=[
        forward_ref_step,
        union_step,
        annotated_step,
        business_step,
        python_step,
    ]
)

# Wire up references
for step in pipeline.steps:
    step.pipeline = pipeline


# 6. Use everything together
customer_schema = BusinessSchema(
    entity_name="Customer",
    fields=[
        {"name": "id", "type": int, "required": True},
        {"name": "name", "type": str, "required": True},
        {"name": "email", "type": Email, "required": True},
        {"name": "phone", "type": PhoneNumber, "required": False},
        {"name": "balance", "type": Currency, "required": True},
    ],
)

schema = AnySchema(
    spec=customer_schema,
    steps=pipeline.steps,
    adapter=business_schema_adapter,
)

print("PyArrow Schema:")
print(schema.to_arrow())

print("\nPolars Schema:")
print(schema.to_polars())
```
