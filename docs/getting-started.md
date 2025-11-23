# Getting Started

This guide will walk you through the basics of using anyschema to convert type specifications to dataframe schemas.

## Installation

!!! note "Development Status"
    `anyschema` is still in early development and not on PyPI yet. You can install it directly from GitHub:

```bash
pip install git+https://github.com/FBruzzesi/anyschema.git
```

For Pydantic support (recommended):

```bash
pip install "anyschema[pydantic] @ git+https://github.com/FBruzzesi/anyschema.git"
```

## Basic Usage

### Using Pydantic Models

The most common way to use anyschema is with Pydantic models:

```python
from anyschema import AnySchema
from pydantic import BaseModel, PositiveInt, Field
from datetime import datetime


class Student(BaseModel):
    name: str
    age: PositiveInt
    email: str
    enrollment_date: datetime
    gpa: float = Field(ge=0.0, le=4.0)
    classes: list[str]


# Create an AnySchema instance
schema = AnySchema(spec=Student)

# Convert to different dataframe schemas
pa_schema = schema.to_arrow()  # PyArrow schema
pl_schema = schema.to_polars()  # Polars schema
pd_schema = schema.to_pandas()  # Pandas dtype mapping
```

### Using Python Dictionaries

You can also use simple Python dictionaries:

```python
from anyschema import AnySchema

spec = {
    "name": str,
    "age": int,
    "score": float,
    "active": bool,
}

schema = AnySchema(spec=spec)
print(schema.to_arrow())
# name: string
# age: int64
# score: double
# active: bool
```

### Using Ordered Lists

For cases where order matters, use a list of tuples:

```python
from anyschema import AnySchema

spec = [
    ("id", int),
    ("name", str),
    ("created", datetime),
]

schema = AnySchema(spec=spec)
```

## Type Mappings

anyschema automatically maps Python and Pydantic types to appropriate dataframe dtypes:

### Basic Types

| Python Type | Narwhals/PyArrow Type |
|-------------|----------------------|
| `int` | `Int64` |
| `float` | `Float64` |
| `str` | `String` |
| `bool` | `Boolean` |
| `bytes` | `Binary` |
| `object` | `Object` |

### Temporal Types

| Python Type | Narwhals/PyArrow Type |
|-------------|----------------------|
| `datetime` | `Datetime(time_unit='us')` |
| `date` | `Date` |
| `time` | `Time` |
| `timedelta` | `Duration` |

### Pydantic Types

| Pydantic Type | Narwhals/PyArrow Type |
|---------------|----------------------|
| `PositiveInt` | `UInt64` |
| `NegativeInt` | `Int64` |
| `PositiveFloat` | `Float64` |
| `NaiveDatetime` | `Datetime` |
| `PastDate` | `Date` |
| `FutureDate` | `Date` |
| `PastDatetime` | `Datetime` |
| `FutureDatetime` | `Datetime` |

### Container Types

| Python Type | Narwhals/PyArrow Type |
|-------------|----------------------|
| `list[T]` | `List(T)` |
| `tuple[T, ...]` | `List(T)` |
| `tuple[T1, T2, T3]` | `Array(T, shape=3)` (if all same type) |
| `Sequence[T]` | `List(T)` |
| `Iterable[T]` | `List(T)` |

### Complex Types

```python
from pydantic import BaseModel
from anyschema import AnySchema


# Nested models become Struct types
class Address(BaseModel):
    street: str
    city: str
    zipcode: str


class Person(BaseModel):
    name: str
    age: int
    address: Address  # This becomes a Struct


schema = AnySchema(spec=Person)
print(schema.to_arrow())
# name: string
# age: int64
# address: struct<street: string, city: string, zipcode: string>
#   child 0, street: string
#   child 1, city: string
#   child 2, zipcode: string
```

## Working with Constraints

anyschema intelligently handles Pydantic field constraints:

### Integer Constraints

```python
from pydantic import BaseModel, Field
from anyschema import AnySchema


class DataModel(BaseModel):
    # Positive integers become unsigned types
    positive: int = Field(gt=0)  # → UInt64

    # Small range integers get optimized types
    small_positive: int = Field(ge=0, le=255)  # → UInt8
    small_signed: int = Field(ge=-128, le=127)  # → Int8

    # Regular integers
    regular: int  # → Int64


schema = AnySchema(spec=DataModel)
pl_schema = schema.to_polars()
print(pl_schema)
# Schema([
#     ('positive', UInt64),
#     ('small_positive', UInt8),
#     ('small_signed', Int8),
#     ('regular', Int64)
# ])
```

### Annotated Types

```python
from typing import Annotated
from annotated_types import Gt, Ge, Lt, Le, Interval
from anyschema import AnySchema


spec = {
    "positive": Annotated[int, Gt(0)],  # → UInt64
    "byte": Annotated[int, Interval(ge=0, le=255)],  # → UInt8
    "percentage": Annotated[int, Ge(0), Le(100)],  # → UInt8
}

schema = AnySchema(spec=spec)
print(schema.to_arrow())
```

## Optional Types

Optional types are automatically handled - the `None` option is extracted and the underlying type is used:

```python
from pydantic import BaseModel
from anyschema import AnySchema


class OptionalFields(BaseModel):
    required_name: str
    optional_age: int | None  # → Int64 (None is stripped)
    optional_email: str | None  # → String (None is stripped)


schema = AnySchema(spec=OptionalFields)
print(schema.to_polars())
# Schema([
#     ('required_name', String),
#     ('optional_age', Int64),      # No "nullable" in dtype
#     ('optional_email', String)     # No "nullable" in dtype
# ])
```

!!! note "Note on Nullability"
    anyschema extracts the non-None type from Optional/Union types. The nullability information is not encoded in the Narwhals dtype itself, but is typically handled at the dataframe level when creating actual data.

## Using with Narwhals

Since anyschema uses Narwhals internally, you can also work directly with Narwhals schemas:

```python
from narwhals.schema import Schema
import narwhals as nw
from anyschema import AnySchema

# Create a Narwhals schema directly
nw_schema = Schema(
    {
        "name": nw.String(),
        "age": nw.Int64(),
        "scores": nw.List(nw.Float64()),
    }
)

# Pass it to AnySchema (it's a no-op internally)
schema = AnySchema(spec=nw_schema)

# Convert to any backend
pa_schema = schema.to_arrow()
pl_schema = schema.to_polars()
```

## Output Formats

### PyArrow Schema

```python
pa_schema = schema.to_arrow()
# Returns: pyarrow.Schema
# Use with: PyArrow tables, Parquet files, DuckDB, etc.
```

### Polars Schema

```python
pl_schema = schema.to_polars()
# Returns: polars.Schema
# Use with: Polars DataFrames, LazyFrames
```

### Pandas Schema

```python
pd_schema = schema.to_pandas()
# Returns: dict[str, pd.ArrowDtype | str | type]
# Use with: pandas DataFrame dtypes parameter

import pandas as pd

df = pd.DataFrame(data, dtype=pd_schema)
```

You can also specify the dtype backend:

```python
# Use PyArrow backend
pd_schema = schema.to_pandas(dtype_backend="pyarrow")

# Use numpy backend
pd_schema = schema.to_pandas(dtype_backend="numpy")
```

## Complete Example

Here's a complete example that shows the full workflow:

```python
from datetime import datetime
from pydantic import BaseModel, PositiveInt, Field, EmailStr
from anyschema import AnySchema
import polars as pl


# Define your data model
class Transaction(BaseModel):
    transaction_id: int
    user_id: PositiveInt
    amount: float = Field(ge=0)
    timestamp: datetime
    status: str
    tags: list[str]


# Create schema converter
schema = AnySchema(spec=Transaction)

# Get Polars schema
pl_schema = schema.to_polars()
print("Polars Schema:")
print(pl_schema)

# Create a Polars DataFrame with the schema
data = {
    "transaction_id": [1, 2, 3],
    "user_id": [101, 102, 103],
    "amount": [99.99, 149.99, 49.99],
    "timestamp": [datetime.now()] * 3,
    "status": ["completed", "pending", "completed"],
    "tags": [["online", "sale"], ["in-store"], ["online"]],
}

df = pl.DataFrame(data, schema=pl_schema)
print("\nDataFrame:")
print(df)
```

## Error Handling

anyschema will raise errors for unsupported types:

```python
from pydantic import AwareDatetime
from anyschema import AnySchema


class Model(BaseModel):
    timestamp: AwareDatetime  # Unsupported!


try:
    schema = AnySchema(spec=Model)
except Exception as e:
    print(f"Error: {e}")
    # Error: pydantic AwareDatetime does not specify a fixed timezone.
```

## Next Steps

- Learn about [Architecture](architecture.md) to understand how anyschema works
- Check out [Advanced Usage](advanced.md) for custom parsers and adapters
- Browse the [API Reference](api-reference.md) for detailed documentation
