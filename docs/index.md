# AnySchema: From Type Specifications to Dataframe Schemas

**anyschema** is a Python library that converts from type specifications (like Pydantic models) to native dataframe schemas for popular libraries such as PyArrow, Polars, and Pandas.

!!! caution "Development Status"
    `anyschema` is still in early development and not yet published on PyPI.
    You can install it directly from GitHub:
    ```bash
    python -m pip install git+https://github.com/FBruzzesi/anyschema.git
    ```

## Quick Start

Here's a simple example showing how `anyschema` works:

```python
from anyschema import AnySchema
from pydantic import BaseModel, PositiveInt


class Student(BaseModel):
    name: str
    age: PositiveInt
    classes: list[str]


schema = AnySchema(spec=Student)

# Convert to PyArrow schema
pa_schema = schema.to_arrow()
print(pa_schema)
# Output:
# name: string
# age: uint64
# classes: list<item: string>
#   child 0, item: string

# Convert to Polars schema
pl_schema = schema.to_polars()
print(pl_schema)
# Output:
# Schema([('name', String), ('age', UInt64), ('classes', List(String))])

# Convert to Pandas schema
pd_schema = schema.to_pandas()
print(pd_schema)
# Output:
# {'name': ArrowDtype(string), 'age': ArrowDtype(uint64), 'classes': ArrowDtype(list<item: string>)}
```

## Key Features

- **Multiple Input Formats**: Support for Pydantic models, Python dicts, and lists of field specifications
- **Multiple Output Formats**: Convert to PyArrow, Polars, or Pandas schemas
- **Type-Safe**: Full type hints and runtime type checking
- **Modular Architecture**: Extensible parser pipeline for custom type handling
- **Rich Type Support**: Handles complex types including Optional, Union, List, nested structures, and Pydantic-specific types
- **Narwhals Integration**: Leverages [Narwhals](https://narwhals-dev.github.io/narwhals/) as the intermediate representation

## Why anyschema?

The project was inspired by a [Talk Python podcast episode](https://www.youtube.com/live/wuGirNCyTxA?t=2880s) featuring the creator of [LanceDB](https://github.com/lancedb/lancedb), who mentioned the need to convert from Pydantic models to PyArrow schemas.

This challenge led to a realization: such conversion could be generalized to many dataframe libraries by using Narwhals as an intermediate representation. **anyschema** makes this conversion seamless and extensible.

## Core Concepts

### Type Parsers (Steps)

Parser steps are modular components that convert Python type annotations to Narwhals dtypes. Each parser handles specific type patterns:

- **ForwardRefStep**: Resolves forward references
- **UnionTypeStep**: Handles `Union` and `Optional` types
- **AnnotatedStep**: Extracts metadata from `typing.Annotated`
- **AnnotatedTypesStep**: Refines types based on constraints
- **PydanticTypeStep**: Handles Pydantic-specific types
- **PyTypeStep**: Handles basic Python types (fallback)

Learn more about how these work together in the [Architecture](architecture.md) section.

### Spec Adapters

Adapters convert input specifications into a common format that the parser pipeline can process:

- **pydantic_adapter**: Extracts field information from Pydantic models
- **into_ordered_dict_adapter**: Handles Python dicts and lists

See the [API Reference](api-reference.md#spec-adapters) for detailed documentation.

## Use Cases

### Data Engineering

Convert Pydantic models to PyArrow schemas for efficient data processing:

```python
from anyschema import AnySchema
from pydantic import BaseModel


class Event(BaseModel):
    timestamp: datetime
    user_id: int
    event_type: str
    metadata: dict


# Get PyArrow schema for Parquet writing
arrow_schema = AnySchema(spec=Event).to_arrow()
```

See [Getting Started](getting-started.md#output-formats) for more details on output formats.

### Data Validation Pipelines

Use Pydantic for validation and anyschema for schema generation:

```python
from anyschema import AnySchema
from pydantic import BaseModel, Field


class Measurement(BaseModel):
    sensor_id: str
    value: float = Field(ge=0.0)
    unit: str


# Generate schema for database or dataframe library
polars_schema = AnySchema(spec=Measurement).to_polars()
```

Learn about [working with constraints](getting-started.md#working-with-constraints) in the Getting Started guide.

### API to DataFrame

Convert API response schemas to dataframe schemas:

```python
from anyschema import AnySchema
from pydantic import BaseModel


class APIResponse(BaseModel):
    id: int
    name: str
    tags: list[str]
    metadata: dict | None


# Get Pandas schema for DataFrame creation
pandas_schema = AnySchema(spec=APIResponse).to_pandas()
```

See the [Getting Started](getting-started.md) guide for more examples.

## Next Steps

- **[Getting Started](getting-started.md)**: Learn the basics and explore type mappings
- **[Architecture](architecture.md)**: Understand the internal design and components
- **[Advanced Usage](advanced.md)**: Create custom parser steps and adapters
- **[API Reference](api-reference.md)**: Complete API documentation

## Contributing

Contributions are welcome! Please check out the [GitHub repository](https://github.com/FBruzzesi/anyschema) to get started.

## License

This project is licensed under the MIT License.
