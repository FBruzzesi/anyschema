# Advanced Usage

This guide covers advanced topics including custom parser steps, custom spec adapters, and extending anyschema for your specific use cases.

Before diving into advanced topics, make sure you understand the [Architecture](architecture.md) and have gone through the [Getting Started](getting-started.md) guide.

## Custom Parser Steps

Creating custom parser steps allows you to add support for new type systems or handle special types in your own way. Parser steps implement the [ParserStep](api-reference.md#parserstep-base-class) interface described in the API reference.

### Basic Custom Parser

Here's a simple custom parser for a hypothetical custom type:

```python
from typing import Any
from narwhals.dtypes import DType
import narwhals as nw
from anyschema.parsers import ParserStep, ParserPipeline, PyTypeStep


class Color:
    """A custom type representing a color."""

    pass


class ColorStep(ParserStep):
    """Parser for Color types."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        """Parse Color to String dtype.

        Arguments:
            input_type: The type to parse.
            metadata: Optional metadata associated with the type.

        Returns:
            String dtype for Color types, None otherwise.
        """
        if input_type is Color:
            return nw.String()
        return None


# Create a pipeline with the custom parser
color_step = ColorStep()
python_step = PyTypeStep()
pipeline = ParserPipeline(steps=[color_step, python_step])

# Wire up pipeline references
color_step.pipeline = pipeline
python_step.pipeline = pipeline

# Test it
result = pipeline.parse(Color)
print(result)  # String
```

### Custom Parser with Nested Types

This example shows how to handle a custom generic type. Note how we use `self.pipeline.parse()` for recursion, as explained in the [Architecture](architecture.md#recursion-and-nested-types) page:

```python
from typing import Any, get_args, get_origin
from narwhals.dtypes import DType
import narwhals as nw
from anyschema.parsers import ParserStep


class MyList:
    """A custom list-like type."""

    pass


class MyListStep(ParserStep):
    """Parser for MyList[T] generic types."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        """Parse MyList[T] to List dtype.

        This parser handles custom generic types by recursively parsing
        the inner type through the pipeline.
        """
        origin = get_origin(input_type)

        if origin is MyList:
            # Get the inner type (e.g., T in MyList[T])
            args = get_args(input_type)
            if args:
                inner_type = args[0]
                # Recursively parse the inner type
                inner_dtype = self.pipeline.parse(inner_type, metadata=metadata)
                return nw.List(inner_dtype)
            else:
                # MyList without type parameter
                return nw.List(nw.Object())

        return None
```

### Custom Parser with Metadata Handling

This example shows how to use metadata to refine type parsing. For more on metadata flow, see the [Architecture](architecture.md#metadata-preservation) section:

```python
from typing import Any, Annotated
from narwhals.dtypes import DType
import narwhals as nw
from anyschema.parsers import ParserStep


class SmallInt:
    """Marker for small integers."""

    pass


class BigInt:
    """Marker for big integers."""

    pass


class CustomConstraintStep(ParserStep):
    """Parser that uses metadata to choose integer size."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        """Parse integers with size constraints.

        Uses metadata to determine whether to use Int32 or Int64.
        """
        if input_type is int and metadata:
            for item in metadata:
                if item is SmallInt:
                    return nw.Int32()
                elif item is BigInt:
                    return nw.Int64()

        return None


# Usage with typing.Annotated
SmallInteger = Annotated[int, SmallInt]
BigInteger = Annotated[int, BigInt]
```

### Custom Parser for Third-Party Types

Integrate third-party libraries with anyschema:

```python
from typing import Any
from narwhals.dtypes import DType
import narwhals as nw
from anyschema.parsers import ParserStep


class PandasCategoricalStep(ParserStep):
    """Parser for pandas Categorical types."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        """Parse pd.CategoricalDtype to Categorical dtype.

        This allows using pandas types in your schemas.
        """
        try:
            import pandas as pd

            if isinstance(input_type, type) and issubclass(
                input_type, pd.CategoricalDtype
            ):
                # Note: Narwhals Categorical dtype doesn't take categories
                return nw.Categorical()
        except ImportError:
            pass

        return None
```

### Combining Multiple Custom Parsers

Here's how to combine multiple custom parsers:

```python
from anyschema import AnySchema
from anyschema.parsers import (
    ParserPipeline,
    ForwardRefStep,
    UnionTypeStep,
    AnnotatedStep,
    PyTypeStep,
)


# Create all parsers
forward_ref_step = ForwardRefStep()
union_step = UnionTypeStep()
annotated_step = AnnotatedStep()
color_step = ColorStep()
my_list_step = MyListStep()
python_step = PyTypeStep()

# Create pipeline with custom parsers
custom_pipeline = ParserPipeline(
    steps=[
        forward_ref_step,
        union_step,
        annotated_step,
        color_step,  # Our custom parsers
        my_list_step,  # before the fallback
        python_step,  # Fallback
    ]
)

# Wire up pipeline references
for step in custom_pipeline.steps:
    step.pipeline = custom_pipeline

# Use the custom pipeline
schema = AnySchema(
    spec={"color": Color, "items": MyList[int]},
    steps=custom_pipeline.steps,
)
```

## Custom Spec Adapters

Custom adapters allow you to convert from any specification format to anyschema's internal format. Adapters follow the [Adapter](api-reference.md#adapter) signature described in the API reference.

### Basic Custom Adapter

Here's a simple adapter for a custom schema format:

```python
from typing import Iterator
from anyschema import AnySchema


class SimpleSchema:
    """A simple schema format."""

    def __init__(self, fields):
        self.fields = fields


def simple_schema_adapter(spec: SimpleSchema) -> Iterator[tuple[str, type, tuple]]:
    """Adapter for SimpleSchema format.

    Arguments:
        spec: A SimpleSchema instance.

    Yields:
        Tuples of (field_name, field_type, metadata).
    """
    for field in spec.fields:
        yield field["name"], field["type"], ()


# Usage
schema_spec = SimpleSchema(
    fields=[
        {"name": "id", "type": int},
        {"name": "name", "type": str},
    ]
)

schema = AnySchema(spec=schema_spec, adapter=simple_schema_adapter)
print(schema.to_arrow())
```

### Adapter with Metadata Conversion

This example shows how to convert schema metadata to anyschema metadata:

```python
from typing import Iterator, Annotated
from anyschema import AnySchema


class FieldWithConstraints:
    """A field with type and constraints."""

    def __init__(self, name: str, type_: type, min_val=None, max_val=None):
        self.name = name
        self.type = type_
        self.min_val = min_val
        self.max_val = max_val


class SchemaWithConstraints:
    """A schema format that includes constraints."""

    def __init__(self, fields):
        self.fields = fields


def constrained_adapter(
    spec: SchemaWithConstraints,
) -> Iterator[tuple[str, type, tuple]]:
    """Adapter that converts constraints to metadata.

    Arguments:
        spec: A SchemaWithConstraints instance.

    Yields:
        Tuples of (field_name, field_type, metadata).
    """
    for field in spec.fields:
        metadata = []

        if field.min_val is not None:
            metadata.append(("min", field.min_val))
        if field.max_val is not None:
            metadata.append(("max", field.max_val))

        yield field.name, field.type, tuple(metadata)


# Usage
schema_spec = SchemaWithConstraints(
    fields=[
        FieldWithConstraints("age", int, min_val=0, max_val=120),
        FieldWithConstraints("name", str),
    ]
)

schema = AnySchema(spec=schema_spec, adapter=constrained_adapter)
```

### Adapter for Nested Structures

Handle nested schemas with a recursive adapter:

```python
from typing import Iterator, Any
from anyschema import AnySchema


class NestedSchema:
    """A schema that can contain nested schemas."""

    def __init__(self, fields):
        self.fields = fields


def nested_adapter(spec: NestedSchema) -> Iterator[tuple[str, type, tuple]]:
    """Adapter for nested schema structures.

    Arguments:
        spec: A NestedSchema instance.

    Yields:
        Tuples of (field_name, field_type, metadata).
    """
    for field_name, field_value in spec.fields.items():
        if isinstance(field_value, NestedSchema):
            # For nested schemas, convert them to dict representation
            # that anyschema can handle
            nested_dict = {
                name: type_ for name, type_, _ in nested_adapter(field_value)
            }
            yield field_name, dict, ()  # Or handle as struct
        else:
            yield field_name, field_value, ()
```

### Adapter for Dataclass-like Structures

Convert from dataclass-like structures:

```python
from typing import Iterator
from dataclasses import dataclass, fields as dc_fields
from anyschema import AnySchema


@dataclass
class DataclassSpec:
    """A dataclass used as a schema specification."""

    id: int
    name: str
    active: bool


def dataclass_adapter(spec: type) -> Iterator[tuple[str, type, tuple]]:
    """Adapter for dataclass specifications.

    Arguments:
        spec: A dataclass class.

    Yields:
        Tuples of (field_name, field_type, metadata).
    """
    for field in dc_fields(spec):
        yield field.name, field.type, ()


# Usage
schema = AnySchema(spec=DataclassSpec, adapter=dataclass_adapter)
print(schema.to_arrow())
```

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

## Next Steps

- **[API Reference](api-reference.md)**: Complete API documentation with detailed docstrings
- **[Architecture](architecture.md)**: Deep dive into the internal design and parser pipeline
- **[Getting Started](getting-started.md)**: Review basic usage examples
- **Repository Tests**: Look at the test files in the [GitHub repository](https://github.com/FBruzzesi/anyschema) for more examples
