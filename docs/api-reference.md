# API Reference

This page provides detailed documentation for all public APIs in anyschema.

For conceptual explanations, see the [Architecture](architecture.md) page. For practical examples, see [Getting Started](getting-started.md) and [Advanced Usage](advanced.md).

## Core Classes

### AnySchema

::: anyschema.AnySchema

## Parser Steps

Parser steps are the building blocks of the type parsing pipeline. Each step handles specific type patterns. For more details on how these work together, see the [Parser Pipeline](architecture.md#parser-pipeline) section in the Architecture guide.

### ParserStep (Base Class)

::: anyschema.parsers.ParserStep

### ParserPipeline

::: anyschema.parsers.ParserPipeline

### Built-in Parser Steps

#### ForwardRefStep

::: anyschema.parsers.ForwardRefStep

#### UnionTypeStep

::: anyschema.parsers.UnionTypeStep

#### AnnotatedStep

::: anyschema.parsers.AnnotatedStep

#### PyTypeStep

::: anyschema.parsers.PyTypeStep

### Parser Pipeline Factory

#### make_pipeline

::: anyschema.parsers.make_pipeline

## Spec Adapters

Adapters convert various input specifications into a normalized format for parsing. Learn how to create custom adapters in the [Advanced Usage](advanced.md#custom-spec-adapters) guide.

### pydantic_adapter

::: anyschema.adapters.pydantic_adapter

### into_ordered_dict_adapter

::: anyschema.adapters.into_ordered_dict_adapter

## Exceptions

### UnavailablePipelineError

::: anyschema.exceptions.UnavailablePipelineError

### UnsupportedDTypeError

::: anyschema.exceptions.UnsupportedDTypeError

## Type Aliases

The following type aliases are used throughout the anyschema codebase:

### Spec

The `Spec` type represents valid input specifications:

```python
Spec = Union[
    Schema,  # Narwhals Schema
    type[BaseModel],  # Pydantic model class
    Mapping[str, type],  # Dict of field_name -> type
    Sequence[tuple[str, type]],  # List of (field_name, type) tuples
]
```

### IntoParserPipeline

The `IntoParserPipeline` type represents valid parser pipeline specifications:

```python
IntoParserPipeline = Union[
    Literal["auto"],  # Automatic parser selection
    Sequence[ParserStep],  # Custom sequence of parser steps
]
```

### Adapter

The `Adapter` type represents a function that adapts a spec into field specifications:

```python
Adapter = Callable[[Any], Iterator[tuple[str, type, tuple]]]
```

Each adapter yields tuples of:
- `field_name` (str): The name of the field
- `field_type` (type): The type annotation of the field
- `metadata` (tuple): Metadata associated with the field

### FieldSpecIterable

The `FieldSpecIterable` type represents the output of an adapter:

```python
FieldSpecIterable = Iterator[tuple[str, type, tuple]]
```

## Usage Examples

### Basic Usage

```python
from anyschema import AnySchema
from pydantic import BaseModel


class User(BaseModel):
    id: int
    name: str


schema = AnySchema(spec=User)

# Convert to different formats
arrow_schema = schema.to_arrow()
polars_schema = schema.to_polars()
pandas_schema = schema.to_pandas()
```

### Using Custom Parser Steps

```python
from anyschema import AnySchema
from anyschema.parsers import ParserStep, PyTypeStep, make_pipeline
import narwhals as nw


class MyCustomStep(ParserStep):
    def parse(self, input_type, metadata=()):
        if input_type is MyCustomType:
            return nw.String()
        return None


# Create custom pipeline
custom_pipeline = make_pipeline([MyCustomStep(), PyTypeStep()])

schema = AnySchema(
    spec={"field": MyCustomType},
    steps=custom_pipeline.steps,
)
```

### Using Custom Adapters

```python
from anyschema import AnySchema


def my_adapter(spec):
    for field in spec.fields:
        yield field.name, field.type, ()


schema = AnySchema(
    spec=my_custom_spec,
    adapter=my_adapter,
)
```

## See Also

- **[Getting Started](getting-started.md)**: Learn the basics with practical examples
- **[Architecture](architecture.md)**: Understand the internal design and parser pipeline
- **[Advanced Usage](advanced.md)**: Create custom parser steps and adapters
