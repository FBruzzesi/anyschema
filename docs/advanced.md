# Advanced Usage

This guide covers advanced topics including creating custom type parsers and spec adapters to extend anyschema's functionality.

## Custom Type Parsers

Custom parsers allow you to handle types that aren't supported out of the box. This is useful for:
- Third-party library types
- Domain-specific types
- Custom business logic for type mapping

### Basic Custom Parser

Here's a simple custom parser that handles a custom type:

```python
from anyschema.parsers import TypeParser
import narwhals as nw
from typing import Any
from narwhals.dtypes import DType


class PercentageType:
    """Custom type representing a percentage."""

    pass


class PercentageParser(TypeParser):
    """Parser that converts PercentageType to Float64."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        if input_type is PercentageType:
            # Store percentages as float
            return nw.Float64()

        # This parser doesn't handle this type
        return None


# Use the custom parser
from anyschema.parsers import create_parser_chain, PyTypeParser
from anyschema import AnySchema

parsers = [
    PercentageParser(),
    PyTypeParser(),
]

chain = create_parser_chain(parsers)

# Test the parser
spec = {
    "name": str,
    "score": PercentageType,
}

schema = AnySchema(spec=spec, parsers=parsers)
print(schema.to_arrow())
# name: string
# score: double
```

### Parser with Nested Types

For parsers that handle container types, you need to recursively call the parser chain:

```python
from typing import Any, get_args, get_origin
import narwhals as nw
from narwhals.dtypes import DType
from anyschema.parsers import TypeParser


class SpecialList:
    """Custom list type that we want to handle specially."""

    pass


class SpecialListParser(TypeParser):
    """Parser that handles SpecialList[T] types."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        origin = get_origin(input_type)

        # Check if this is SpecialList[T]
        if origin is SpecialList:
            args = get_args(input_type)
            if args:
                # Recursively parse the inner type
                inner_dtype = self.parser_chain.parse(args[0], metadata, strict=True)
                # For this example, just return a regular List
                return nw.List(inner_dtype)

        return None


# Example usage
from anyschema.parsers import create_parser_chain, PyTypeParser

parsers = [
    SpecialListParser(),
    PyTypeParser(),
]

chain = create_parser_chain(parsers)

# Note: Using SpecialList[int] would require proper __class_getitem__ implementation
# This is just to demonstrate the concept
```

### Parser with Metadata Handling

You can create parsers that respond to custom metadata:

```python
from dataclasses import dataclass
from typing import Any
import narwhals as nw
from narwhals.dtypes import DType
from anyschema.parsers import TypeParser


@dataclass
class Precision:
    """Custom metadata to specify float precision."""

    decimals: int


class PrecisionAwareParser(TypeParser):
    """Parser that handles float types with precision metadata."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        if input_type is float:
            # Check for Precision metadata
            for item in metadata:
                if isinstance(item, Precision):
                    if item.decimals <= 7:  # Single precision
                        return nw.Float32()
                    else:  # Double precision
                        return nw.Float64()

            # Default float handling
            return nw.Float64()

        return None


# Usage with Annotated types
from typing import Annotated
from anyschema import AnySchema
from anyschema.parsers import create_parser_chain, PyTypeParser

spec = {
    "low_precision": Annotated[float, Precision(decimals=4)],
    "high_precision": Annotated[float, Precision(decimals=10)],
    "regular": float,
}

parsers = [PrecisionAwareParser(), PyTypeParser()]
schema = AnySchema(spec=spec, parsers=parsers)

pl_schema = schema.to_polars()
print(pl_schema)
# Schema([
#     ('low_precision', Float32),
#     ('high_precision', Float64),
#     ('regular', Float64)
# ])
```

### Parser for Third-Party Types

Here's an example of handling types from a third-party library:

```python
import narwhals as nw
from narwhals.dtypes import DType
from anyschema.parsers import TypeParser
from typing import Any


# Imagine these are from a third-party library
class IPv4Address:
    pass


class IPv6Address:
    pass


class EmailAddress:
    pass


class NetworkTypesParser(TypeParser):
    """Parser for network-related custom types."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        # Map all to String for storage
        if input_type in {IPv4Address, IPv6Address, EmailAddress}:
            return nw.String()

        return None


# Usage
from anyschema import AnySchema
from anyschema.parsers import create_parser_chain, PyTypeParser

parsers = [
    NetworkTypesParser(),
    PyTypeParser(),
]

spec = {
    "id": int,
    "email": EmailAddress,
    "ipv4": IPv4Address,
    "ipv6": IPv6Address,
}

schema = AnySchema(spec=spec, parsers=parsers)
print(schema.to_arrow())
# id: int64
# email: string
# ipv4: string
# ipv6: string
```

### Combining Multiple Custom Parsers

You can compose multiple custom parsers for different purposes:

```python
from anyschema.parsers import (
    create_parser_chain,
    ForwardRefParser,
    UnionTypeParser,
    AnnotatedParser,
    PyTypeParser,
)

# Create a custom parser chain
parsers = [
    ForwardRefParser(),  # Resolve forward references
    UnionTypeParser(),  # Handle Optional/Union
    AnnotatedParser(),  # Extract Annotated types
    NetworkTypesParser(),  # Your custom network types
    PercentageParser(),  # Your custom percentage type
    PrecisionAwareParser(),  # Your custom precision handling
    PyTypeParser(),  # Fallback to standard types
]

chain = create_parser_chain(parsers)

# Now use with AnySchema
from anyschema import AnySchema

spec = {
    "email": EmailAddress | None,  # Union handling + custom type
    "score": PercentageType,  # Custom type
    "value": Annotated[float, Precision(decimals=4)],  # Metadata handling
}

schema = AnySchema(spec=spec, parsers=parsers)
```

## Custom Spec Adapters

Custom adapters allow you to extract field information from any specification format.

### Basic Custom Adapter

An adapter is simply a function that yields `(field_name, field_type, metadata)` tuples:

```python
from typing import Generator


class MyCustomModel:
    """Custom model class from hypothetical library."""

    def __init__(self):
        self._fields = {
            "id": (int, {}),
            "name": (str, {}),
            "age": (int, {"min": 0, "max": 150}),
        }

    def get_fields(self):
        return self._fields


def my_custom_adapter(
    spec: MyCustomModel,
) -> Generator[tuple[str, type, tuple], None, None]:
    """Adapter for MyCustomModel."""
    for field_name, (field_type, constraints) in spec.get_fields().items():
        # Convert constraints dict to metadata tuple
        metadata = tuple(constraints.items()) if constraints else ()
        yield field_name, field_type, metadata


# Usage
from anyschema import AnySchema

my_model = MyCustomModel()
schema = AnySchema(spec=my_model, adapter=my_custom_adapter)

print(schema.to_arrow())
# id: int64
# name: string
# age: int64
```

### Adapter with Metadata Conversion

Convert custom metadata formats to `annotated_types` constraints:

```python
from typing import Generator
from annotated_types import Ge, Le


class SchemaWithConstraints:
    """Custom schema format with constraints."""

    fields = [
        {"name": "id", "type": int},
        {"name": "age", "type": int, "min": 0, "max": 150},
        {"name": "score", "type": float, "min": 0.0, "max": 100.0},
    ]


def constraints_adapter(
    spec: SchemaWithConstraints,
) -> Generator[tuple[str, type, tuple], None, None]:
    """Adapter that converts min/max constraints to annotated_types."""
    for field in spec.fields:
        field_name = field["name"]
        field_type = field["type"]

        # Build metadata from constraints
        metadata = []
        if "min" in field:
            metadata.append(Ge(field["min"]))
        if "max" in field:
            metadata.append(Le(field["max"]))

        yield field_name, field_type, tuple(metadata)


# Usage
from anyschema import AnySchema
from anyschema.parsers import create_parser_chain

schema_spec = SchemaWithConstraints()
parsers = create_parser_chain("auto", spec_type="python")
schema = AnySchema(spec=schema_spec, adapter=constraints_adapter, parsers=parsers)

pl_schema = schema.to_polars()
print(pl_schema)
# Schema([
#     ('id', Int64),
#     ('age', UInt8),      # Optimized based on constraints!
#     ('score', Float64)
# ])
```

### Adapter for Nested Structures

Handle nested or complex structures:

```python
from typing import Generator, Any


class NestedSchema:
    """Schema format with nested structures."""

    def __init__(self):
        self.fields = {
            "user": {
                "type": "struct",
                "fields": {
                    "name": str,
                    "age": int,
                },
            },
            "scores": {
                "type": "list",
                "element_type": float,
            },
            "active": bool,
        }


def nested_adapter(
    spec: NestedSchema,
) -> Generator[tuple[str, type, tuple], None, None]:
    """Adapter that handles nested structures."""

    def resolve_type(field_def: Any) -> type:
        """Resolve nested type definitions."""
        if isinstance(field_def, dict):
            if field_def.get("type") == "struct":
                # For structs, we'd need to create a nested model
                # For simplicity, just return dict
                return dict
            elif field_def.get("type") == "list":
                element_type = field_def.get("element_type")
                return list[element_type]
            else:
                return object
        else:
            return field_def

    for field_name, field_def in spec.fields.items():
        field_type = resolve_type(field_def)
        yield field_name, field_type, ()


# Usage
from anyschema import AnySchema

nested_spec = NestedSchema()
schema = AnySchema(spec=nested_spec, adapter=nested_adapter)

print(schema.to_arrow())
# user: map
# scores: list<item: double>
# active: bool
```

### Adapter for DataClass-like Structures

Here's an adapter for Python dataclasses (as an alternative approach):

```python
from dataclasses import dataclass, fields
from typing import Generator, Any


@dataclass
class Product:
    id: int
    name: str
    price: float
    in_stock: bool


def dataclass_adapter(spec: type) -> Generator[tuple[str, type, tuple], None, None]:
    """Adapter for Python dataclasses."""
    if not hasattr(spec, "__dataclass_fields__"):
        raise ValueError(f"{spec} is not a dataclass")

    for field in fields(spec):
        field_name = field.name
        field_type = field.type
        # Could extract metadata from field.metadata if present
        metadata = tuple(field.metadata.values()) if field.metadata else ()

        yield field_name, field_type, metadata


# Usage
from anyschema import AnySchema

schema = AnySchema(spec=Product, adapter=dataclass_adapter)
print(schema.to_arrow())
# id: int64
# name: string
# price: double
# in_stock: bool
```

## Complete Custom Example

Here's a complete example combining custom parsers and adapters:

```python
from typing import Any, Generator
from dataclasses import dataclass
import narwhals as nw
from narwhals.dtypes import DType
from anyschema.parsers import TypeParser, create_parser_chain, PyTypeParser
from anyschema import AnySchema


# 1. Define custom types
class CurrencyType:
    """Represents a monetary value."""

    pass


class PhoneNumberType:
    """Represents a phone number."""

    pass


# 2. Create custom parser
class BusinessTypesParser(TypeParser):
    """Parser for business domain types."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        if input_type is CurrencyType:
            # Store currency as Decimal for precision
            return nw.Decimal()

        if input_type is PhoneNumberType:
            # Store phone numbers as strings
            return nw.String()

        return None


# 3. Create custom spec format
@dataclass
class BusinessField:
    name: str
    type: type
    required: bool = True


class BusinessSchema:
    """Custom schema format for business applications."""

    def __init__(self, name: str, fields: list[BusinessField]):
        self.name = name
        self.fields = fields


# 4. Create custom adapter
def business_adapter(
    spec: BusinessSchema,
) -> Generator[tuple[str, type, tuple], None, None]:
    """Adapter for BusinessSchema format."""
    for field in spec.fields:
        # Could use field.required to determine nullability in the future
        yield field.name, field.type, ()


# 5. Use everything together
# Define a business schema
product_schema = BusinessSchema(
    name="Product",
    fields=[
        BusinessField("id", int),
        BusinessField("name", str),
        BusinessField("price", CurrencyType),
        BusinessField("phone", PhoneNumberType),
        BusinessField("in_stock", bool),
    ],
)

# Create custom parser chain
parsers = [
    BusinessTypesParser(),
    PyTypeParser(),
]

# Create AnySchema with custom adapter and parsers
schema = AnySchema(
    spec=product_schema,
    adapter=business_adapter,
    parsers=parsers,
)

# Convert to different formats
print("PyArrow Schema:")
print(schema.to_arrow())
# id: int64
# name: string
# price: decimal128(38, 9)
# phone: string
# in_stock: bool

print("\nPolars Schema:")
print(schema.to_polars())
# Schema([('id', Int64), ('name', String), ('price', Decimal), ('phone', String), ('in_stock', Boolean)])
```

## Best Practices

### For Custom Parsers

1. **Return None Early**: If you don't handle a type, return `None` immediately
   ```python
   def parse(self, input_type, metadata=()):
       if input_type is not MyType:
           return None
       # ... handle MyType
   ```

2. **Use Strict Mode for Recursion**: Always use `strict=True` when calling the chain recursively
   ```python
   inner_dtype = self.parser_chain.parse(inner_type, metadata, strict=True)
   ```

3. **Preserve Metadata**: If unwrapping a type, pass metadata through
   ```python
   return self.parser_chain.parse(unwrapped_type, metadata, strict=True)
   ```

4. **Handle Edge Cases**: Consider empty metadata, invalid types, etc.

5. **Document Behavior**: Clearly document what types your parser handles in the docstring

### For Custom Adapters

1. **Validate Input**: Check that the spec is the expected type
   ```python
   def my_adapter(spec):
       if not isinstance(spec, MySpecType):
           raise TypeError(f"Expected MySpecType, got {type(spec)}")
       # ...
   ```

2. **Preserve Order**: Use OrderedDict or maintain field order
   ```python
   from collections import OrderedDict

   fields = OrderedDict(spec.fields)
   ```

3. **Convert Metadata**: Convert custom constraint formats to standard ones
   ```python
   from annotated_types import Ge, Le

   if "min" in constraints:
       metadata.append(Ge(constraints["min"]))
   ```

4. **Handle Missing Data**: Provide sensible defaults
   ```python
   field_type = field.get("type", object)
   metadata = field.get("constraints", ())
   ```

## Testing Custom Components

### Testing Custom Parsers

```python
import narwhals as nw
from anyschema.parsers import ParserChain


def test_custom_parser():
    parser = MyCustomParser()
    chain = ParserChain([parser])
    parser.parser_chain = chain

    # Test successful parsing
    result = parser.parse(MyCustomType)
    assert result == nw.String()

    # Test unsupported type
    result = parser.parse(UnsupportedType)
    assert result is None


def test_custom_parser_with_metadata():
    parser = MyCustomParser()
    chain = ParserChain([parser])
    parser.parser_chain = chain

    result = parser.parse(MyCustomType, metadata=(MyConstraint(),))
    assert isinstance(result, nw.DType)
```

### Testing Custom Adapters

```python
def test_custom_adapter():
    spec = MyCustomModel()

    results = list(my_custom_adapter(spec))

    assert len(results) == 3
    assert results[0] == ("field1", str, ())
    assert results[1] == ("field2", int, ())


def test_adapter_with_anyschema():
    from anyschema import AnySchema

    spec = MyCustomModel()
    schema = AnySchema(spec=spec, adapter=my_custom_adapter)

    pa_schema = schema.to_arrow()
    assert len(pa_schema) == 3
    assert pa_schema.field("field1").type == pa.string()
```

## Real-World Example: JSON Schema Adapter

Here's a practical example of an adapter for JSON Schema:

```python
from typing import Generator, Any


def json_schema_adapter(spec: dict) -> Generator[tuple[str, type, tuple], None, None]:
    """Adapter for JSON Schema format."""

    # Mapping from JSON Schema types to Python types
    TYPE_MAP = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    if spec.get("type") != "object":
        raise ValueError("Only object-type JSON schemas are supported")

    properties = spec.get("properties", {})

    for field_name, field_schema in properties.items():
        json_type = field_schema.get("type", "string")
        python_type = TYPE_MAP.get(json_type, object)

        # Handle array types
        if json_type == "array" and "items" in field_schema:
            item_type = field_schema["items"].get("type", "string")
            item_python_type = TYPE_MAP.get(item_type, object)
            python_type = list[item_python_type]

        yield field_name, python_type, ()


# Usage
from anyschema import AnySchema

json_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "scores": {"type": "array", "items": {"type": "number"}},
    },
}

schema = AnySchema(spec=json_schema, adapter=json_schema_adapter)
print(schema.to_arrow())
# name: string
# age: int64
# scores: list<item: double>
```

## Next Steps

- See [Architecture](architecture.md) to understand how the parsers and adapters fit together
- Browse the [API Reference](api-reference.md) for detailed API documentation
- Check out the examples in the repository for more inspiration
