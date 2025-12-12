# Advanced Usage

This guide covers advanced topics including custom parser steps, custom spec adapters, and extending anyschema for your
specific use cases.

It might be useful to review the [Architecture](../architecture.md) and have gone through the
[Getting Started](getting-started.md) guide before diving into advanced topics.

## Custom Parser Steps

Creating custom parser steps allows you to add support for new type systems or handle special types in your own way.
Parser steps should inherit from the [ParserStep][api-parser-step] base class
and implement the `parse` method with the following signature:

```python
from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


def parse(
    self,
    input_type: FieldType,
    constraints: FieldConstraints,
    metadata: FieldMetadata,
) -> DType | None:
    ...
```

### Basic Custom Parser

Here's a simple custom parser for a hypothetical custom type:

```python exec="true" source="above" result="python" session="custom-parser"
import narwhals as nw
from anyschema.parsers import make_pipeline, ParserStep, PyTypeStep
from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


class Color:
    """A custom type representing a color."""

    pass


class ColorStep(ParserStep):
    """Parser for Color types."""

    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> DType | None:
        """Parse Color to String dtype.

        Arguments:
            input_type: The type to parse.
            constraints: Constraints associated with the type.
            metadata: Custom metadata dictionary.

        Returns:
            String dtype for Color types, None otherwise.
        """
        if input_type is Color:
            return nw.String()
        return None


# Create a simple pipeline with the custom parser
color_step = ColorStep()
python_step = PyTypeStep()
pipeline = make_pipeline(steps=[color_step, python_step])

result = pipeline.parse(Color, constraints=(), metadata={})
print(result)
```

### Custom Parser with Nested Types

This example shows how to handle a custom generic type. Note how we use
`self.pipeline.parse(..., constraints=constraints, metadata=metadata)` for recursion, as
explained in the [Architecture](../architecture.md#recursion-and-nested-types) page:

```python exec="true" source="above" result="python" session="custom-parser"
from typing import Any, TypeVar, get_args, get_origin

import narwhals as nw
from anyschema.parsers import ParserStep

from anyschema.typing import FieldConstraints, FieldMetadata, FieldType

T = TypeVar("T")

class MyList[T]:
    """A custom list-like type."""

    pass


class MyListStep(ParserStep):
    """Parser for MyList[T] generic types."""

    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> nw.dtypes.DType | None:
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
                inner_dtype = self.pipeline.parse(inner_type, constraints=constraints, metadata=metadata)
                return nw.List(inner_dtype)
            else:
                # MyList without type parameter
                return nw.List(nw.Object())

        return None

my_list_step = MyListStep()
python_step = PyTypeStep()
pipeline = make_pipeline(steps=[my_list_step, python_step])
result = pipeline.parse(MyList[int], (), {})
print(result)
```

### Custom Parser with Metadata Handling

This example shows how to use metadata to refine type parsing. For more on metadata flow, see the
[Architecture](../architecture.md#metadata-preservation) section:

```python exec="true" source="above" result="python" session="custom-parser"
from typing import Any, Annotated

import narwhals as nw
from anyschema.parsers import AnnotatedStep, ParserStep, PyTypeStep
from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


class SmallInt:
    """Marker for small integers."""

    pass


class BigInt:
    """Marker for big integers."""

    pass


class CustomConstraintStep(ParserStep):
    """Parser that uses constraints to choose integer size."""

    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> DType | None:
        """Parse integers with size constraints.

        Uses constraints to determine whether to use Int32 or Int64.
        """
        if input_type is int and constraints:
            for constraint in constraints:
                if constraint is SmallInt:
                    return nw.Int32()
                elif constraint is BigInt:
                    return nw.Int64()

        return None


# Usage with typing.Annotated
SmallInteger = Annotated[int, SmallInt]
BigInteger = Annotated[int, BigInt]

# Create a pipeline with the custom parser
annotated_step = AnnotatedStep()
custom_constraint_step = CustomConstraintStep()
python_step = PyTypeStep()
pipeline = make_pipeline(steps=[annotated_step, custom_constraint_step, python_step])

print(f"SmallInteger dtype: {pipeline.parse(SmallInteger, (), {})}")
print(f"BigInteger dtype: {pipeline.parse(BigInteger, (), {})}")
```

### Combining Multiple Custom Parsers

Here's how to combine multiple custom parsers:

```python exec="true" source="above" result="python" session="custom-parser"
from anyschema import AnySchema
from anyschema.parsers import (
    make_pipeline,
    ParserPipeline,
    ForwardRefStep,
    UnionTypeStep,
    AnnotatedStep,
    PyTypeStep,
)

# Create pipeline with custom parsers
custom_pipeline = make_pipeline(
    steps=[
        ForwardRefStep(),
        UnionTypeStep(),
        AnnotatedStep(),
        ColorStep(),  # Our custom parsers
        MyListStep(),  # before the fallback
        PyTypeStep(),  # Fallback
    ]
)

# Use the custom pipeline
schema = AnySchema(
    spec={"color": Color, "items": MyList[int]},
    steps=custom_pipeline.steps,
)
print(schema.to_arrow())
```

## Custom Spec Adapters

Custom adapters allow you to convert from any specification format to anyschema's internal format. Adapters need to
follow the [Adapter](../api-reference/adapters.md#adapters-specification) signature described in the API reference.

### Basic Custom Adapter

Here's a simple adapter for a custom schema format:

```python exec="true" source="above" result="python" session="custom-adapter"
from typing import TypedDict
from anyschema import AnySchema
from anyschema.typing import FieldSpecIterable


class CustomFieldSpec(TypedDict):
    """Field specification in the custom schema format."""

    name: str
    type: type


class SimpleSchema:
    """A simple schema format."""

    def __init__(self, fields: list[CustomFieldSpec]) -> None:
        self.fields = fields


def simple_schema_adapter(spec: SimpleSchema) -> FieldSpecIterable:
    """Adapter for SimpleSchema format.

    Arguments:
        spec: A SimpleSchema instance.

    Yields:
        Tuples of (field_name, field_type, constraints, metadata).
    """
    for field in spec.fields:
        yield field["name"], field["type"], (), {}


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

```python exec="true" source="above" result="python" session="custom-adapter"
from typing import Annotated
from anyschema import AnySchema
from anyschema.typing import FieldSpecIterable


class FieldWithConstraints:
    """A field with type and constraints."""

    def __init__(
        self,
        name: str,
        type_: type,
        min_val: int | None = None,
        max_val: int | None = None,
    ):
        self.name = name
        self.type = type_
        self.min_val = min_val
        self.max_val = max_val


class SchemaWithConstraints:
    """A schema format that includes constraints."""

    def __init__(self, fields: list[FieldWithConstraints]) -> None:
        self.fields = fields


def constrained_adapter(spec: SchemaWithConstraints) -> FieldSpecIterable:
    """Adapter that converts constraints to the constraints tuple.

    Arguments:
        spec: A SchemaWithConstraints instance.

    Yields:
        Tuples of (field_name, field_type, constraints, metadata).
    """
    for field in spec.fields:
        constraints = []

        if field.min_val is not None:
            constraints.append(("min", field.min_val))
        if field.max_val is not None:
            constraints.append(("max", field.max_val))

        yield field.name, field.type, tuple(constraints), {}


schema_spec = SchemaWithConstraints(
    fields=[
        FieldWithConstraints("age", int, min_val=0, max_val=120),
        FieldWithConstraints("name", str),
    ]
)

schema = AnySchema(spec=schema_spec, adapter=constrained_adapter)
print(schema.to_arrow())
```

Notice that we don't have a parser step to handle the metadata in this example.
You would need to implement one if you want to process custom metadata.
See an example in the dedicated [Custom Parser Steps](#custom-parser-with-metadata-handling) section.

### Adapter for Nested Structures

Handle nested schemas with a recursive adapter by dynamically creating TypedDict classes:

```python exec="true" source="above" result="python" session="custom-adapter"
from typing import Any, TypedDict
from anyschema import AnySchema
from anyschema.typing import FieldSpecIterable


class NestedSchema:
    """A schema that can contain nested schemas."""

    def __init__(self, fields: dict[str, Any]) -> None:
        self.fields = fields


def nested_adapter(spec: NestedSchema) -> FieldSpecIterable:
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
            nested_dict = {
                name: type_ for name, type_, _, _ in nested_adapter(field_value)
            }
            # Create a dynamic TypedDict with the nested fields
            nested_typed_dict = TypedDict(
                f"{field_name.title()}TypedDict",  # Generate a unique name
                nested_dict,  # Field name -> type mapping
            )
            yield field_name, nested_typed_dict, (), {}
        else:
            yield field_name, field_value, (), {}


schema_spec = NestedSchema(
    fields={
        "id": int,
        "profile": NestedSchema(
            fields={
                "name": str,
                "age": int,
            }
        ),
    }
)
schema = AnySchema(spec=schema_spec, adapter=nested_adapter)
print(schema.to_arrow())
```

### Adapter for JSON Schema

Here's a practical example of adapting from JSON Schema:

```python exec="true" source="above" result="python" session="custom-adapter"
import json
from anyschema import AnySchema
from anyschema.typing import FieldSpecIterable


def json_schema_adapter(spec: str) -> FieldSpecIterable:
    """Adapter for JSON Schema format.

    Arguments:
        spec: A JSON Schema with "type": "object" and "properties".

    Yields:
        Tuples of (field_name, field_type, constraints, metadata).
    """
    spec = json.loads(spec)
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

        yield field_name, python_type, (), {}


json_schema = json.dumps(
    {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "email": {"type": "string"},
        },
        "required": ["id", "name"],
    }
)

schema = AnySchema(spec=json_schema, adapter=json_schema_adapter)
print(schema.to_arrow())
```

[api-parser-step]: ../api-reference/parsers.md#anyschema.parsers.ParserStep
