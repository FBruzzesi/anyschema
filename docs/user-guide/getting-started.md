# Getting Started

This guide will help you get started with `anyschema` and explore its core functionality.

## Basic Usage

`anyschema` accepts specifications in multiple formats including Pydantic models, SQLAlchemy tables, TypedDict,
dataclasses, attrs classes, and plain Python dicts (and more to come, see [anyschema#11](https://github.com/FBruzzesi/anyschema/issues/11)).

Let's explore each approach and when to use it.

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

The `AnySchema` object also provides access to detailed field information through the `fields` attribute:

```python exec="true" source="above" result="python" session="basic-pydantic"
print(schema.fields["id"])
```

You can also provide field descriptions and other metadata. For Pydantic models, the `description` parameter of
`Field()` is automatically extracted:

```python exec="true" source="above" result="python" session="basic-pydantic-description"
from anyschema import AnySchema
from pydantic import BaseModel, Field


class Product(BaseModel):
    id: int = Field(description="Unique product identifier")
    name: str = Field(description="Product name")
    price: float = Field(description="Product price in USD")


schema = AnySchema(spec=Product)
for field_name, field in schema.fields.items():
    print(f"{field_name}: {field.description!r}")
```

See [Metadata](metadata.md#the-anyfield-class) for more details on the `AnyField` class and [supported metadata keys](metadata.md#supported-metadata-keys).

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

### With attrs classes

[attrs](https://www.attrs.org/en/stable/) provides a powerful way to write classes with less boilerplate:

```python exec="true" source="above" result="python" session="basic-attrs"
from anyschema import AnySchema
from attrs import define


@define
class User:
    id: int
    username: str
    email: str
    is_active: bool


schema = AnySchema(spec=User)
print(schema.to_arrow())
```

### With SQLAlchemy Tables

[SQLAlchemy](https://www.sqlalchemy.org/) provides powerful ORM and Core table definitions that can be used directly:

=== "ORM (DeclarativeBase)"

    ```python exec="true" source="above" result="python" session="basic-sqlalchemy-orm"
    from anyschema import AnySchema
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    from sqlalchemy import String


    class Base(DeclarativeBase):
        pass


    class User(Base):
        __tablename__ = "user"

        id: Mapped[int] = mapped_column(primary_key=True)
        username: Mapped[str] = mapped_column(String(50))
        email: Mapped[str]
        is_active: Mapped[bool]


    schema = AnySchema(spec=User)
    print(schema.to_arrow())
    ```

=== "Core (Table)"

    ```python exec="true" source="above" result="python" session="basic-sqlalchemy-core"
    from anyschema import AnySchema
    from sqlalchemy import Table, Column, Integer, String, Boolean, MetaData


    metadata = MetaData()
    user_table = Table(
        "user",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("username", String(50)),
        Column("email", String(100)),
        Column("is_active", Boolean),
    )

    schema = AnySchema(spec=user_table)
    print(schema.to_arrow())
    ```

SQLAlchemy support includes comprehensive type mapping for numeric types, strings, dates, binary data, JSON, UUIDs,
Enums, and PostgreSQL-specific types like `ARRAY`.

Both dynamic-length arrays (converted to `List`) and fixed-dimension arrays (converted to `Array`) are supported.

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

## Understanding nullability

One of the key features of `anyschema` is accurate nullability tracking:

* When you declare a field as `str`, it's non-nullable.
* When you declare it as `str | None` (or `Optional[str]`), it's nullable.

This distinction is especially valuable when working with PyArrow, which supports `not null` constraints:

```python exec="true" source="above" result="python" session="nullability-intro"
from pydantic import BaseModel
from anyschema import AnySchema
import pyarrow as pa


class User(BaseModel):
    name: str  # Non-nullable
    email: str | None  # Nullable


users = [
    User(name="Alice", email="alice@example.com"),
    User(name="Bob", email=None),
]

# Without anyschema: both fields nullable (PyArrow default)
default_table = pa.Table.from_pylist([user.model_dump() for user in users])
print("Default PyArrow schema: both fields are nullable")
print(default_table.schema)

# With anyschema: explicit nullability from type annotations
schema = AnySchema(spec=User)
explicit_table = pa.Table.from_pylist(
    [user.model_dump() for user in users],
    schema=schema.to_arrow(),
)
print("\nWith anyschema: name is not nullable, email is")
print(explicit_table.schema)
```

Notice how `name` is now marked as `not null`, accurately reflecting the constraint from your Pydantic model!

This also means that if you try to validate data with `name=None`, Pydantic will reject it:

```python exec="true" source="above" result="python" session="nullability-intro"
try:
    User(name=None, email="nobody@example.com")
except Exception as e:
    print(f"Validation error: {e}")
```

See the [Metadata guide](metadata.md#nullable) for more details on nullable semantics and how to override
type-based inference.

## Nested Types

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

=== "attrs"

    ```python exec="true" source="above" result="python" session="nested-attrs"
    from anyschema import AnySchema
    from attrs import define


    @define
    class Address:
        street: str
        city: str
        country: str


    @define
    class Person:
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

Constraints are processed by the [`AnnotatedTypesStep`][api-annotated-types-step]

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

[api-annotated-types-step]: ../api-reference/parsers.md#anyschema.parsers.annotated_types.AnnotatedTypesStep
