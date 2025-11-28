# Getting Started

This guide will help you get started with `anyschema` and explore its core functionality.

## Basic Usage

`anyschema` accepts specifications in multiple formats (and more to come, see [anyschema[#11](https://github.com/FBruzzesi/anyschema/issues/11)])
and converts them to dataframe schemas. Let's explore each approach and when to use it.

### With Pydantic Models

The most common way to use anyschema is with Pydantic models:

```python exec="true" source="above" session="basic-pydantic"
from anyschema import AnySchema
from pydantic import BaseModel


class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool


schema = AnySchema(spec=User)
```

Convert to different schema formats:

=== "pyarrow"

    ```python exec="true" source="above" result="python" session="basic-pydantic"
    print(schema.to_arrow())
    ```

=== "polars"

    ```python exec="true" source="above" result="python" session="basic-pydantic"
    print(schema.to_polars())
    ```

=== "pandas"

    ```python exec="true" source="above" result="python" session="basic-pydantic"
    print(schema.to_pandas())
    ```

### With TypedDict

You can use `TypedDict` for a lightweight way to define typed structures:

```python exec="true" source="above" result="python" session="basic-typeddict"
from anyschema import AnySchema
from typing_extensions import TypedDict


class User(TypedDict):
    id: int
    username: str
    email: str
    is_active: bool


schema = AnySchema(spec=User)
print(schema.to_arrow())
```

### With dataclasses

You can also use plain Python dataclasses

```python exec="true" source="above" result="python" session="basic-dataclass"
from anyschema import AnySchema
from dataclasses import dataclass


@dataclass
class User:
    id: int
    username: str
    email: str
    is_active: bool


schema = AnySchema(spec=User)
print(schema.to_arrow())
```

### With Python Mappings

You can also use plain Python mappings (such as dictionaries):

```python exec="true" source="above" result="python" session="basic-mapping"
from anyschema import AnySchema

spec = {
    "id": int,
    "username": str,
    "email": str,
    "is_active": bool,
}

schema = AnySchema(spec=spec)
print(schema.to_arrow())
```

### With Sequence of Tuples

Or use a sequence of `(name, type)` tuples:

```python exec="true" source="above" result="python" session="basic-sequence"
from anyschema import AnySchema

spec = [
    ("id", int),
    ("username", str),
    ("email", str),
    ("is_active", bool),
]

schema = AnySchema(spec=spec)
print(schema.to_polars())
```

### Nested Types

You can use nested structures with Pydantic models, dataclasses, or TypedDict:

=== "Pydantic"

    ```python exec="true" source="above" session="nested-pydantic"
    from anyschema import AnySchema
    from pydantic import BaseModel


    class Address(BaseModel):
        street: str
        city: str
        country: str


    class Person(BaseModel):
        name: str
        age: int
        addresses: list[Address]


    schema = AnySchema(spec=Person)
    pa_schema = schema.to_arrow()
    print(pa_schema)
    ```

=== "TypedDict"

    ```python exec="true" source="above" result="python" session="nested-typeddict"
    from anyschema import AnySchema
    from typing_extensions import TypedDict


    class Address(TypedDict):
        street: str
        city: str
        country: str


    class Person(TypedDict):
        name: str
        age: int
        addresses: list[Address]


    schema = AnySchema(spec=Person)
    pa_schema = schema.to_arrow()
    print(pa_schema)
    ```

As you can see, a field (`addresses`) that contains a nested structure is correctly represented as a nested struct in
the schema.

## Working with (Integer) Constraints

Constraints are processed by the [`AnnotatedTypesStep`](../api-reference/parsers.md#anyschema.parsers.annotated_types.AnnotatedTypesStep)
parser step, which refines types based on their metadata.
The following examples demonstrate how constraints are handled.

Pydantic's constrained integer types are automatically converted to appropriate unsigned or signed integers:

```python exec="true" source="above" result="python" session="integer-constraints"
from anyschema import AnySchema
from pydantic import BaseModel, PositiveInt, NonNegativeInt


class Metrics(BaseModel):
    count: PositiveInt
    offset: NonNegativeInt
    delta: int


schema = AnySchema(spec=Metrics)
arrow_schema = schema.to_arrow()
print(arrow_schema)
```

### Using Annotated Types

You can also use `typing.Annotated` with constraint metadata:

```python exec="true" source="above" result="python" session="annotated-types"
from typing import Annotated
from anyschema import AnySchema
from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str
    price: Annotated[float, Field(gt=0)]  # Price must be positive
    quantity: Annotated[
        int, Field(ge=0, lt=100)
    ]  # Quantity must be non-negative, and say we limit it to <100


schema = AnySchema(spec=Product)
print(schema.to_polars())
```

## Using Narwhals Directly

You can also work with Narwhals schemas directly (and pass them to `AnySchema`, which acts as a no-op in this case):

```python exec="true" source="above" session="narwhals"
from narwhals.schema import Schema
import narwhals as nw
from anyschema import AnySchema

# Create a Narwhals schema
nw_schema = Schema(
    {
        "id": nw.Int64(),
        "name": nw.String(),
        "scores": nw.List(nw.Float64()),
    }
)

schema = AnySchema(spec=nw_schema)
```

## Pandas output format

!!! abstract "pandas schema"
    Unlike pyarrow and polars, pandas does not have a native schema representation.
    Therefore our output is a dictionary mapping column names to dtypes.

<!-- rumdl-disable MD005 -->
!!! warning "pandas multiple `dtype_backend`'s"
    pandas supports multiple dtype backends that affect types nullability:

    - `None` (default): Uses standard NumPy dtypes (not nullable).
    - `"numpy_nullable"`* Uses pandas nullable dtypes (e.g., `Int64` instead of `int64`).
    - `"pyarrow"`: Uses PyArrow-backed dtypes (better performance, native nullable support).

    You can specify which backend to use via the `dtype_backend` parameter, either for all fields together, or for each
    field individually.
<!-- rumdl-enable MD005 -->

Let's see it in practice:

```python exec="true" source="above" result="python" session="pandas-format"
from anyschema import AnySchema
from pydantic import BaseModel, PositiveInt, NonNegativeInt


class Metrics(BaseModel):
    count: PositiveInt
    offset: NonNegativeInt
    delta: int


schema = AnySchema(spec=Metrics)
pd_schema = schema.to_pandas(
    dtype_backend=(
        "pyarrow",  # `count` will be mapped to a pyarrow dtype
        "numpy_nullable",  # `offset` will be mapped to a pandas nullable numpy dtype
        None,  # `delta` will be mapped to the default pandas numpy dtype
    )
)
print(pd_schema)
```

## Error Handling

anyschema will raise exceptions for unsupported types:

```python
from anyschema import AnySchema

try:
    # This will fail - set is not supported
    schema = AnySchema(spec={"invalid": set})
    arrow_schema = schema.to_arrow()
except NotImplementedError as e:
    print(f"Error: {e}")
    # Error: No parser in the pipeline could handle type: builtins.set
```

For Union types with more than two members (excluding None), an error is raised:

```python
from anyschema import AnySchema
from anyschema.exceptions import UnsupportedDTypeError

try:
    # Union[int, str, float] is not supported
    schema = AnySchema(spec={"field": int | str | float})
except UnsupportedDTypeError as e:
    print(f"Error: {e}")
```
