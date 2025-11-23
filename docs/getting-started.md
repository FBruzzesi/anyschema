# Getting Started

This guide will help you get started with **anyschema** and explore its core functionality.

## Installation

!!! caution "Development Status"
    `anyschema` is currently in early development and not yet published on PyPI.

Install directly from GitHub:

```bash
python -m pip install git+https://github.com/FBruzzesi/anyschema.git
```

For Pydantic support (recommended), install with the `pydantic` extra:

```bash
python -m pip install "git+https://github.com/FBruzzesi/anyschema.git[pydantic]"
```

## Basic Usage

### With Pydantic Models

The most common way to use anyschema is with Pydantic models:

```python
from anyschema import AnySchema
from pydantic import BaseModel


class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool


schema = AnySchema(spec=User)

# Convert to different schema formats
arrow_schema = schema.to_arrow()
polars_schema = schema.to_polars()
pandas_schema = schema.to_pandas()
```

### With Python Dictionaries

You can also use plain Python dictionaries:

```python
from anyschema import AnySchema

spec = {
    "id": int,
    "username": str,
    "email": str,
    "is_active": bool,
}

schema = AnySchema(spec=spec)
arrow_schema = schema.to_arrow()
```

### With Lists of Tuples

Or use a list of `(name, type)` tuples:

```python
from anyschema import AnySchema

spec = [
    ("id", int),
    ("username", str),
    ("email", str),
    ("is_active", bool),
]

schema = AnySchema(spec=spec)
polars_schema = schema.to_polars()
```

## Type Mappings

anyschema converts Python type annotations to Narwhals dtypes, which are then converted to the target dataframe library's native types. For more details on how this process works, see the [Architecture](architecture.md) page.

### Basic Python Types

anyschema supports a wide range of Python types:

| Python Type | Narwhals DType | PyArrow Type | Polars Type |
|------------|----------------|--------------|-------------|
| `int` | `Int64` | `int64` | `Int64` |
| `float` | `Float64` | `double` | `Float64` |
| `str` | `String` | `string` | `String` |
| `bool` | `Boolean` | `bool` | `Boolean` |
| `bytes` | `Binary` | `binary` | `Binary` |
| `object` | `Object` | `pyobject` | `Object` |
| `Decimal` | `Decimal` | `decimal128` | `Decimal` |

### Temporal Types

| Python Type | Narwhals DType | PyArrow Type | Polars Type |
|------------|----------------|--------------|-------------|
| `date` | `Date` | `date32` | `Date` |
| `datetime` | `Datetime("us")` | `timestamp[us]` | `Datetime("us")` |
| `time` | `Time` | `time64[ns]` | `Time` |
| `timedelta` | `Duration` | `duration[us]` | `Duration("us")` |

### Pydantic Types

When using Pydantic models, specialized types are automatically handled. These types are processed by the [PydanticTypeStep](architecture.md#5-pydantictypestep) parser:

| Pydantic Type | Narwhals DType | Description |
|--------------|----------------|-------------|
| `PositiveInt` | `UInt64` | Unsigned integer (positive only) |
| `NegativeInt` | `Int64` | Signed integer (negative only) |
| `NonNegativeInt` | `UInt64` | Unsigned integer (zero or positive) |
| `NonPositiveInt` | `Int64` | Signed integer (zero or negative) |
| `PositiveFloat` | `Float64` | Positive float |
| `NegativeFloat` | `Float64` | Negative float |

### Container Types

anyschema supports nested and container types:

| Python Type | Narwhals DType | PyArrow Type | Polars Type |
|------------|----------------|--------------|-------------|
| `list[T]` | `List(T)` | `list<T>` | `List(T)` |
| `Sequence[T]` | `List(T)` | `list<T>` | `List(T)` |
| `Iterable[T]` | `List(T)` | `list<T>` | `List(T)` |
| `tuple[T, ...]` | `List(T)` | `list<T>` | `List(T)` |
| `tuple[T, T, T]` | `Array(T, 3)` | `fixed_size_list<T>[3]` | `Array(T, 3)` |

### Complex Types

```python
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
    metadata: dict


schema = AnySchema(spec=Person)
```

In this example:
- `addresses: list[Address]` becomes `List(Struct)`
- `metadata: dict` becomes `Struct`

## Working with Constraints

Constraints are processed by the [AnnotatedTypesStep](architecture.md#4-annotatedtypesstep) parser, which refines types based on metadata.

### Integer Constraints

Pydantic's constrained integer types are automatically converted to appropriate unsigned or signed integers:

```python
from anyschema import AnySchema
from pydantic import BaseModel, PositiveInt, NonNegativeInt


class Metrics(BaseModel):
    count: PositiveInt  # -> UInt64 (always positive)
    offset: NonNegativeInt  # -> UInt64 (zero or positive)
    delta: int  # -> Int64 (can be negative)


schema = AnySchema(spec=Metrics)
arrow_schema = schema.to_arrow()
print(arrow_schema)
# count: uint64
# offset: uint64
# delta: int64
```

### Using Annotated Types

You can also use `typing.Annotated` with constraint metadata:

```python
from typing import Annotated
from anyschema import AnySchema
from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str
    price: Annotated[float, Field(gt=0)]  # Price must be positive
    quantity: Annotated[int, Field(ge=0)]  # Quantity must be non-negative


schema = AnySchema(spec=Product)
```

## Optional Types

anyschema automatically handles optional (nullable) types. These are processed by the [UnionTypeStep](architecture.md#2-uniontypestep) parser, which extracts the non-None type:

```python
from anyschema import AnySchema
from pydantic import BaseModel


class Article(BaseModel):
    title: str
    subtitle: str | None  # Optional field
    author: str


schema = AnySchema(spec=Article)
arrow_schema = schema.to_arrow()
print(arrow_schema)
# title: string not null
# subtitle: string
# author: string not null
```

Note that PyArrow schemas mark nullable fields automatically, while the underlying type remains the same.

## Using Narwhals Directly

You can also work with Narwhals schemas directly:

```python
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

# Pass it to AnySchema (this is a no-op internally)
schema = AnySchema(spec=nw_schema)

# Convert to target format
arrow_schema = schema.to_arrow()
polars_schema = schema.to_polars()
```

## Output Formats

### PyArrow

```python
pa_schema = schema.to_arrow()
# Returns: pyarrow.Schema
```

Use this for:
- Writing Parquet files
- Working with Apache Arrow
- Interoperability with other Arrow-based tools

### Polars

```python
pl_schema = schema.to_polars()
# Returns: polars.Schema
```

Use this for:
- Creating Polars DataFrames with specific schemas
- Data validation with Polars
- High-performance data processing

### Pandas

```python
pd_schema = schema.to_pandas()
# Returns: dict[str, str | pd.ArrowDtype | type]
```

Use this for:
- Creating Pandas DataFrames with specific dtypes
- Data analysis with Pandas
- Integration with existing Pandas workflows

You can optionally specify a `dtype_backend`:

```python
# Using PyArrow backend
pd_schema = schema.to_pandas(dtype_backend="pyarrow")

# Using NumPy backend
pd_schema = schema.to_pandas(dtype_backend="numpy")
```

## Complete Example

Here's a complete example demonstrating various features:

```python
from datetime import datetime
from anyschema import AnySchema
from pydantic import BaseModel, PositiveInt, Field
from typing import Annotated


class Category(BaseModel):
    id: PositiveInt
    name: str


class Product(BaseModel):
    id: PositiveInt
    name: str
    description: str | None
    price: Annotated[float, Field(gt=0)]
    quantity: Annotated[int, Field(ge=0)]
    categories: list[Category]
    created_at: datetime
    metadata: dict


# Create the schema
schema = AnySchema(spec=Product)

# Convert to PyArrow (useful for Parquet files)
arrow_schema = schema.to_arrow()
print("PyArrow Schema:")
print(arrow_schema)

# Convert to Polars (useful for Polars DataFrames)
polars_schema = schema.to_polars()
print("\nPolars Schema:")
print(polars_schema)

# Convert to Pandas (useful for Pandas DataFrames)
pandas_schema = schema.to_pandas(dtype_backend="pyarrow")
print("\nPandas Schema:")
for field, dtype in pandas_schema.items():
    print(f"  {field}: {dtype}")
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

## Next Steps

- **[Architecture](architecture.md)**: Understand how anyschema works internally with detailed explanations of the parser pipeline
- **[Advanced Usage](advanced.md)**: Create custom parsers and adapters to extend anyschema for your needs
- **[API Reference](api-reference.md)**: Complete API documentation with detailed docstrings
