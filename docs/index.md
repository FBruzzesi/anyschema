# Welcome to anyschema

**anyschema** is a powerful Python library that bridges the gap between type definitions and dataframe schemas. It allows you to convert from type specifications (like Pydantic models or Python mappings) to native dataframe schemas for popular libraries like PyArrow, Polars, and Pandas.

## What is anyschema?

`anyschema` provides a unified interface to convert type specifications into dataframe schemas through [Narwhals](https://narwhals-dev.github.io/narwhals/). This means you can define your data schema once using Pydantic models or Python type annotations, and convert it to any supported dataframe library.

## Quick Example

Let's see how it works with a simple example:

```python
from anyschema import AnySchema
from pydantic import BaseModel, PositiveInt


class Student(BaseModel):
    name: str
    age: PositiveInt
    classes: list[str]


schema = AnySchema(spec=Student)
```

### Convert to PyArrow

```python
pa_schema = schema.to_arrow()
print(pa_schema)
# name: string
# age: uint64
# classes: list<item: string>
#   child 0, item: string
```

### Convert to Polars

```python
pl_schema = schema.to_polars()
print(pl_schema)
# Schema([('name', String), ('age', UInt64), ('classes', List(String))])
```

### Convert to Pandas

```python
pd_schema = schema.to_pandas()
print(pd_schema)
# {'name': ArrowDtype(string), 'age': ArrowDtype(uint64), 'classes': ArrowDtype(list<item: string>)}
```

## Key Features

- **Multiple Input Formats**: Support for Pydantic models, Python mappings, and Narwhals schemas
- **Multiple Output Formats**: Convert to PyArrow, Polars, and Pandas schemas
- **Smart Type Mapping**: Automatically handles Pydantic constraints and converts them to appropriate dtypes
- **Extensible**: Easy to add custom type parsers and adapters
- **Type Safe**: Full type hints support for better IDE integration
- **Narwhals Powered**: Leverages Narwhals for seamless cross-library compatibility

## Installation

!!! note "Development Status"
    `anyschema` is still in early development and not on PyPI yet. You can install it directly from GitHub:

```bash
pip install git+https://github.com/FBruzzesi/anyschema.git
```

### Optional Dependencies

For Pydantic support:

```bash
pip install "anyschema[pydantic] @ git+https://github.com/FBruzzesi/anyschema.git"
```

## Basic Concepts

### Type Parsers

Type parsers are responsible for converting Python type annotations into Narwhals dtypes. anyschema includes several built-in parsers:

- **PyTypeParser**: Handles basic Python types (int, str, float, list, etc.)
- **PydanticTypeParser**: Handles Pydantic-specific types and models
- **AnnotatedParser**: Extracts type and metadata from `typing.Annotated`
- **UnionTypeParser**: Handles Union and Optional types
- **ForwardRefParser**: Resolves forward references
- **AnnotatedTypesParser**: Refines types based on constraints (e.g., `PositiveInt` → `UInt64`)

### Spec Adapters

Spec adapters convert your input specification (Pydantic model, dict, etc.) into a standardized format that the parser chain can process. Built-in adapters include:

- **pydantic_adapter**: Extracts fields from Pydantic models
- **into_ordered_dict_adapter**: Converts Python mappings to field specifications

## Use Cases

### 1. Data Validation Pipelines

Define your data schema once with Pydantic and use it across different dataframe libraries:

```python
from pydantic import BaseModel, Field
from anyschema import AnySchema


class SensorData(BaseModel):
    timestamp: datetime
    sensor_id: int
    temperature: float = Field(ge=-50, le=150)
    humidity: float = Field(ge=0, le=100)


schema = AnySchema(spec=SensorData)

# Use with PyArrow for efficient storage
pa_schema = schema.to_arrow()

# Use with Polars for fast processing
pl_schema = schema.to_polars()
```

### 2. Database Schema Generation

Convert Pydantic models to database schemas:

```python
class User(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    is_active: bool = True


schema = AnySchema(spec=User)
# Use to_arrow() to create database tables with appropriate types
```

### 3. API Response Schemas

Ensure consistency between API models and data processing schemas:

```python
class APIResponse(BaseModel):
    status: str
    data: list[dict[str, Any]]
    timestamp: datetime


# Convert to dataframe schema for processing
schema = AnySchema(spec=APIResponse)
```

## Why anyschema?

The initial motivation for this project came from a [Talk Python podcast episode](https://www.youtube.com/live/wuGirNCyTxA?t=2880s) featuring the creator of [LanceDB](https://github.com/lancedb/lancedb), who mentioned the need to convert Pydantic models to PyArrow schemas.

This sparked the idea: could this be generalized to support any dataframe library? By leveraging [Narwhals](https://narwhals-dev.github.io/narwhals/) as an intermediate representation, anyschema makes this possible!

## Next Steps

- [Getting Started](getting-started.md) - Learn the basics with detailed examples
- [Architecture](architecture.md) - Understand how anyschema works under the hood
- [Advanced Usage](advanced.md) - Learn about custom parsers and adapters
- [API Reference](api-reference.md) - Complete API documentation
