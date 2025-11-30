# anyschema: From Type Specifications to Dataframe Schemas

`anyschema` is a Python library that enables conversions from type specifications (such as Pydantic models) to native
dataframe schemas (such as PyArrow, Polars, and Pandas).

!!! warning "Development Status"
    `anyschema` is still in early development and possibly unstable.

## Installation

`anyschema` is available on [pypi](https://pypi.org/project/anyschema/), and it can be installed directly via
any package manager. For instance:

=== "pip"

    ```bash
    python -m pip install anyschema
    ```

=== "uv"

    ```bash
    uv pip install anyschema
    ```

We suggest to install also `pydantic` or `attrs` to follow along with the examples.

- `anyschema` interoperability with pydantic models requires `pydantic>=2.0.0`.
- `anyschema` interoperability with attrs classes requires `attrs>=24.0.0`.

=== "pip"

    ```bash
    python -m pip install "anyschema[pydantic]"
    # or
    python -m pip install "anyschema[attrs]"
    ```

=== "uv"

    ```bash
    uv pip install "anyschema[pydantic]"
    # or
    uv pip install "anyschema[attrs]"
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

## When to use `anyschema`

`anyschema` is designed for scenarios where some type specifications (e.g. a Pydantic Model) want to be used as a single
source of truth for both validation and (dataframe) schema generation.

The typical use cases are: Data pipelines, API to database workflows, schema generation, type-safe data processing.

## Key Features

- **Multiple Input Formats**: Support for Pydantic models, attrs classes, TypedDict, dataclasses, Python mappings and
    sequence of field specifications.
- **Multiple Output Formats**: Convert to PyArrow, Polars, or Pandas schemas.
- **Modular Architecture**: Extensible parser pipeline for custom type handling.
- **Rich Type Support**: Handles complex types including Optional, Union, List, nested structures, Pydantic-specific
    types, and attrs classes.
- **Narwhals Integration**: Leverages [Narwhals](https://narwhals-dev.github.io/narwhals/) as the intermediate
    representation.

## Core Components

### Type Parsers (Steps)

Parser steps are modular components that convert type annotations to Narwhals dtypes. Each parser handles specific type
patterns:

- [`ForwardRefStep`](api-reference/parsers.md#anyschema.parsers.ForwardRefStep): Resolves forward references.
- [`UnionTypeStep`](api-reference/parsers.md#anyschema.parsers.UnionTypeStep): Handles `Union` and `Optional` types.
- [`AnnotatedStep`](api-reference/parsers.md#anyschema.parsers.AnnotatedStep): Extracts metadata from
    `typing.Annotated`.
- [`AnnotatedTypesStep`](api-reference/parsers.md#anyschema.parsers.annotated_types.AnnotatedTypesStep): Refines types
    based on constraints from the `annotated-types` library.
- [`PydanticTypeStep`](api-reference/parsers.md#anyschema.parsers.pydantic.PydanticTypeStep): Handles Pydantic-specific
    types.
- [`PyTypeStep`](api-reference/parsers.md#anyschema.parsers.PyTypeStep): Handles basic Python types (fallback).

Learn more about how these work together in the [Architecture](architecture.md) section.

### Spec Adapters

Adapters convert input specifications into a common format that the parser pipeline can process:

- [`into_ordered_dict_adapter`](api-reference/adapters.md#anyschema.adapters.into_ordered_dict_adapter): Handles Python
    dicts and sequences.
- [`typed_dict_adapter`](api-reference/adapters.md#anyschema.adapters.typed_dict_adapter): Extracts field information from
    TypedDict classes.
- [`dataclass_adapter`](api-reference/adapters.md#anyschema.adapters.dataclass_adapter): Extracts field information from
    dataclasses.
- [`attrs_adapter`](api-reference/adapters.md#anyschema.adapters.attrs_adapter): Extracts field information from
    attrs classes.
- [`pydantic_adapter`](api-reference/adapters.md#anyschema.adapters.pydantic_adapter): Extracts field information from
    Pydantic models.

See the [API Reference](api-reference/adapters.md) for detailed documentation.

## Next Steps

### Learning Path

We recommend following this order to get the most out of anyschema:

1. [Getting Started](user-guide/getting-started.md): Learn the basics.
2. [Architecture](architecture.md): Understand the internal design and how components work together.
3. [Advanced Usage](user-guide/advanced.md): Create custom parser steps and adapters for your specific needs.
4. [Best Practices](user-guide/best-practices.md): Learn patterns and anti-patterns for custom components.
5. [End-to-End Example](user-guide/custom-end-to-end-example.md): See a complete real-world example.

### Reference Materials

- [API Reference](api-reference/index.md): Complete API documentation.
- [Troubleshooting](user-guide/troubleshooting.md): Common issues and solutions.

## Contributing

Contributions are welcome! Please check out the [GitHub repository](https://github.com/FBruzzesi/anyschema) to get
started.

## License

This project is licensed under the Apache-2.0 license.

## Why `anyschema`?

The project was inspired by a [Talk Python podcast episode](https://www.youtube.com/live/wuGirNCyTxA?t=2880s) featuring
the creator of [LanceDB](https://github.com/lancedb/lancedb), who mentioned the need to convert from Pydantic models to
PyArrow schemas.

This challenge led to a realization: such conversion could be generalized to many dataframe libraries by using Narwhals
as an intermediate representation. `anyschema` makes this conversion seamless and extensible.
