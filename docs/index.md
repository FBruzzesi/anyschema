# anyschema: From Type Specifications to Dataframe Schemas

**anyschema** is a Python library that enables conversions from type specifications (such as Pydantic models) to native
dataframe schemas (such as PyArrow, Polars, and Pandas).

!!! warning "Development Status"
    `anyschema` is still in early development and not yet published on PyPI.

    You can install it directly from GitHub:

    ```bash
    python -m pip install git+https://github.com/FBruzzesi/anyschema.git
    ```

    For Pydantic support (recommended), install with the `pydantic` extra:

    ```bash
    python -m pip install "git+https://github.com/FBruzzesi/anyschema.git[pydantic]"
    ```

## Quick Start

Here's a simple example showing how `anyschema` works.

First define the type specification via a Pydantic model and create an `AnySchema` instance from it:

```python exec="true" source="above" session="quickstart"
from anyschema import AnySchema
from pydantic import BaseModel, PositiveInt


class Student(BaseModel):
    name: str
    age: PositiveInt  # (1)
    classes: list[str]


schema = AnySchema(spec=Student)
```

1. By using `PositiveInt` instead of python `int`, we ensure that the age is always a positive integer.
    And we can translate this constraint into the resulting dataframe schema.

Then, you can convert it to different dataframe schemas:

=== "pyarrow"

    ```python exec="true" source="above" result="python" session="quickstart"
    pa_schema = schema.to_arrow()
    print(pa_schema)
    ```

=== "polars"

    ```python exec="true" source="above" result="python" session="quickstart"
    pl_schema = schema.to_polars()
    print(pl_schema)
    ```

=== "pandas"

    ```python exec="true" source="above" result="python" session="quickstart"
    pd_schema = schema.to_pandas()
    print(pd_schema)
    ```

## Key Features

- **Multiple Input Formats**: Support for Pydantic models, Python mappings and sequence of field specifications.
- **Multiple Output Formats**: Convert to PyArrow, Polars, or Pandas schemas.
- **Modular Architecture**: Extensible parser pipeline for custom type handling.
- **Rich Type Support**: Handles complex types including Optional, Union, List, nested structures, and
    Pydantic-specific types.
- **Narwhals Integration**: Leverages [Narwhals](https://narwhals-dev.github.io/narwhals/) as the intermediate
    representation.

## Why anyschema?

The project was inspired by a [Talk Python podcast episode](https://www.youtube.com/live/wuGirNCyTxA?t=2880s) featuring
the creator of [LanceDB](https://github.com/lancedb/lancedb), who mentioned the need to convert from Pydantic models to
PyArrow schemas.

This challenge led to a realization: such conversion could be generalized to many dataframe libraries by using Narwhals
as an intermediate representation. **anyschema** makes this conversion seamless and extensible.

## Core Components

### Type Parsers (Steps)

Parser steps are modular components that convert type annotations to Narwhals dtypes. Each parser handles specific type
patterns:

- `ForwardRefStep`: Resolves forward references
- `UnionTypeStep`: Handles `Union` and `Optional` types
- `AnnotatedStep`: Extracts metadata from `typing.Annotated`
- `AnnotatedTypesStep`: Refines types based on constraints from the `annotated-types` library
- `PydanticTypeStep`: Handles Pydantic-specific types
- `PyTypeStep`: Handles basic Python types (fallback)

Learn more about how these work together in the [Architecture](architecture.md) section.

### Spec Adapters

Adapters convert input specifications into a common format that the parser pipeline can process:

- **into_ordered_dict_adapter**: Handles Python dicts and sequences.
- **pydantic_adapter**: Extracts field information from Pydantic models.

See the [API Reference](api-reference/adapters.md) for detailed documentation.

## Next Steps

- **[Getting Started](user-guide/getting-started.md)**: Learn the basics and explore type mappings
- **[Advanced Usage](user-guide/advanced.md)**: Create custom parser steps and adapters
- **[Architecture](architecture.md)**: Understand the internal design and components
- **[API Reference](api-reference/index.md)**: Complete API documentation

## Contributing

Contributions are welcome! Please check out the [GitHub repository](https://github.com/FBruzzesi/anyschema) to get
started.

## License

This project is licensed under the Apache-2.0 license.
