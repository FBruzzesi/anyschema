# Advanced Usage

This guide covers advanced topics including custom parser steps, custom spec adapters, and extending anyschema for your
specific use cases.

It might be useful to review the [Architecture](architecture.md) and have gone through the
[Getting Started](user-guide/getting-started.md) guide before diving into advanced topics.

## Custom Parser Steps

Creating custom parser steps allows you to add support for new type systems or handle special types in your own way.
Parser steps should inherit from the [ParserStep](../api-reference/parsers.md#parserstep-base-class) base class and
implement the `parse` method with the following signature:

```python
def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
    ...
```

### Basic Custom Parser

Here's a simple custom parser for a hypothetical custom type:

```python exec="true" source="above" result="python" session="custom-parser"
from typing import Any

import narwhals as nw
from anyschema.parsers import make_pipeline, ParserStep, PyTypeStep


class Color:
    """A custom type representing a color."""

    pass


class ColorStep(ParserStep):
    """Parser for Color types."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> nw.dtypes.DType | None:
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


# Create a simple pipeline with the custom parser
color_step = ColorStep()
python_step = PyTypeStep()
pipeline = make_pipeline(steps=[color_step, python_step])

result = pipeline.parse(Color)
print(result)
```

### Custom Parser with Nested Types

This example shows how to handle a custom generic type. Note how we use `self.pipeline.parse()` for recursion, as
explained in the [Architecture](architecture.md#recursion-and-nested-types) page:

```python exec="true" source="above" result="python" session="custom-parser"
from typing import Any, TypeVar, get_args, get_origin

import narwhals as nw
from anyschema.parsers import ParserStep

T = TypeVar("T")

class MyList[T]:
    """A custom list-like type."""

    pass


class MyListStep(ParserStep):
    """Parser for MyList[T] generic types."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> nw.dtypes.DType | None:
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

my_list_step = MyListStep()
python_step = PyTypeStep()
pipeline = make_pipeline(steps=[my_list_step, python_step])
result = pipeline.parse(MyList[int])
print(result)
```

### Custom Parser with Metadata Handling

This example shows how to use metadata to refine type parsing. For more on metadata flow, see the
[Architecture](architecture.md#metadata-preservation) section:

```python exec="true" source="above" result="python" session="custom-parser"
from typing import Any, Annotated

import narwhals as nw
from anyschema.parsers import AnnotatedStep, ParserStep, PyTypeStep


class SmallInt:
    """Marker for small integers."""

    pass


class BigInt:
    """Marker for big integers."""

    pass


class CustomConstraintStep(ParserStep):
    """Parser that uses metadata to choose integer size."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> nw.dtypes.DType | None:
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

# Create a pipeline with the custom parser
annotated_step = AnnotatedStep()
custom_constraint_step = CustomConstraintStep()
python_step = PyTypeStep()
pipeline = make_pipeline(steps=[annotated_step, custom_constraint_step, python_step])

print(f"SmallInteger dtype: {pipeline.parse(SmallInteger)}")
print(f"BigInteger dtype: {pipeline.parse(BigInteger)}")
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
from typing import Iterator, TypedDict
from anyschema import AnySchema
from anyschema.typing import FieldSpec


class CustomFieldSpec(TypedDict):
    """Field specification in the custom schema format."""

    name: str
    type: type


class SimpleSchema:
    """A simple schema format."""

    def __init__(self, fields: list[CustomFieldSpec]) -> None:
        self.fields = fields


def simple_schema_adapter(spec: SimpleSchema) -> Iterator[FieldSpec]:
    """Adapter for SimpleSchema format.

    Arguments:
        spec: A SimpleSchema instance.

    Yields:
        Tuples of (field_name, field_type, metadata).
    """
    for field in spec.fields:
        yield field["name"], field["type"], ()


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
from typing import Iterator, Annotated
from anyschema import AnySchema
from anyschema.typing import FieldSpec


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


def constrained_adapter(spec: SchemaWithConstraints) -> Iterator[FieldSpec]:
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
from typing import Iterator, Any, TypedDict
from anyschema import AnySchema
from anyschema.typing import FieldSpec


class NestedSchema:
    """A schema that can contain nested schemas."""

    def __init__(self, fields: dict[str, Any]) -> None:
        self.fields = fields


def nested_adapter(spec: NestedSchema) -> Iterator[FieldSpec]:
    """Adapter for nested schema structures.

    For nested schemas, we dynamically create a TypedDict so the parser
    can properly extract the field structure.

    Arguments:
        spec: A NestedSchema instance.

    Yields:
        Tuples of (field_name, field_type, metadata).
    """
    for field_name, field_value in spec.fields.items():
        if isinstance(field_value, NestedSchema):
            # For nested schemas, create a TypedDict with the proper structure
            nested_dict = {
                name: type_ for name, type_, _ in nested_adapter(field_value)
            }
            # Create a dynamic TypedDict with the nested fields
            nested_typed_dict = TypedDict(
                f"{field_name.title()}TypedDict",  # Generate a unique name
                nested_dict,  # Field name -> type mapping
            )
            yield field_name, nested_typed_dict, ()
        else:
            yield field_name, field_value, ()


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

### Adapter for Dataclass-like Structures

Convert from dataclass-like structures:

```python exec="true" source="above" result="python" session="custom-adapter"
from typing import Iterator
from dataclasses import dataclass, fields as dc_fields
from anyschema import AnySchema


@dataclass
class DataclassSpec:
    """A dataclass used as a schema specification."""

    id: int
    name: str
    active: bool


def dataclass_adapter(spec: type) -> Iterator[FieldSpec]:
    """Adapter for dataclass specifications.

    Arguments:
        spec: A dataclass class.

    Yields:
        Tuples of (field_name, field_type, metadata).
    """
    for field in dc_fields(spec):
        yield field.name, field.type, ()


schema = AnySchema(spec=DataclassSpec, adapter=dataclass_adapter)
print(schema.to_arrow())
```
