# Metadata

Metadata allows you to provide additional information about fields that influences how they are parsed into
dataframe schemas.

This guide covers how to specify metadata for different specification formats and which metadata keys have special
behavior in `anyschema`.

## Overview

Metadata is a dictionary of key-value pairs attached to individual fields.
While you can store any custom metadata, anyschema recognizes a specific nested structure
with the `"anyschema"` (or `"x-anyschema"` for OpenAPI compatibility) key that modifies parsing behavior.

!!! tip "OpenAPI Compatibility"
    For better integration with OpenAPI tools and specifications, you can use `"x-anyschema"` instead of `"anyschema"`.

    Both work identically. See the [OpenAPI Compatibility](openapi-compatibility.md) guide for more details.

Currently supported special metadata keys:

* `{"anyschema": {"nullable": <bool>, ...}}`: Specifies whether the field can contain null values.
* `{"anyschema": {"unique": <bool>, ...}}`: Specifies whether all values in the field must be unique.
* `{"anyschema": {"description": <str | None>, ...}}`: Provides a human-readable description of the field.
* `{"anyschema": {"time_zone": <str | None>, ...}}`: Specifies timezone for datetime fields.
* `{"anyschema": {"time_unit": <TimeUnit>, ...}}`: Specifies time precision for datetime fields (default: `"us"`).
* `{"anyschema": {"dtype": <DType | str>, ...}}`: Specifies the Narwhals dtype of the field
    (see the [dtype override](#dtype) section).

## The `AnyField` Class

Starting from version 0.3.0, `anyschema` provides a [`AnyField`][anyschema.AnyField] class that encapsulates detailed
information about each field in a schema.

When you create an `AnySchema`, it parses each field into a `AnyField` object that contains:

* `name`: The field name
* `dtype`: The Narwhals data type
* `nullable`: Whether the field accepts null values
* `unique`: Whether values must be unique
* `description`: Human-readable field description
* `metadata`: Custom metadata dictionary (excluding `anyschema` and `x-anyschema` keys)

You can access these fields through the `fields` attribute:

```python exec="true" source="above" result="python" session="field-class-intro"
from typing import Optional
from anyschema import AnySchema

schema = AnySchema(spec={"id": int, "name": str, "email": Optional[str]})

# Access fields
id_field = schema.fields["id"]
print(id_field)

email_field = schema.fields["email"]
print(email_field)
```

## Supported Metadata Keys

!!! info "Metadata Precedence"
    Explicit `anyschema` metadata keys **always take precedence** over values inferred from types.

    For example, setting `{"anyschema": {"nullable": False}}` will make a field non-nullable even if the type
    is `Optional[T]`. This allows you to override type-level inference when needed.

### `nullable`

Specifies whether the field can contain null values.

**Precedence rules** (highest to lowest):

1. Explicit `nullable` metadata key
2. Type inference (`Optional[T]` or `T | None`)
3. Default: `False` (non-nullable by default)

Let's take a look at an example:

```python exec="true" source="above" result="python" session="nullable-example"
from pydantic import BaseModel, Field
from anyschema import AnySchema


class User(BaseModel):
    id: int = Field(json_schema_extra={"anyschema": {"nullable": False}})
    username: str
    email: str | None


schema = AnySchema(spec=User)

for field in schema.fields.values():
    print(f"field '{field.name}' nullable: {field.nullable}")
```

**Overriding type inference with explicit metadata:**

```python exec="true" source="above" result="python" session="nullable-override"
from typing import Optional
from pydantic import BaseModel, Field
from anyschema import AnySchema


class Config(BaseModel):
    # Type says Optional, but metadata overrides to non-nullable
    required_field: Optional[str] = Field(
        json_schema_extra={"anyschema": {"nullable": False}}
    )
    # Type says non-Optional, but metadata overrides to nullable
    optional_field: str = Field(json_schema_extra={"anyschema": {"nullable": True}})


schema = AnySchema(spec=Config)

for field in schema.fields.values():
    print(f"field '{field.name}' nullable: {field.nullable}")
```

#### Understanding nullable semantics

The nullable property reflects whether a field **accepts null values according to the type specification**.
This is particularly important when converting validated data (from Pydantic, attrs, dataclasses) to dataframe schemas.

Consider this example:

```python exec="true" source="above" result="python" session="nullable-semantics"
from pydantic import BaseModel
from anyschema import AnySchema


class User(BaseModel):
    name: str  # Non-nullable: validation will reject None
    email: str | None  # Nullable: None is explicitly allowed


schema = AnySchema(spec=User)

for field in schema.fields.values():
    print(f"field '{field.name}' nullable: {field.nullable}")
```

**Why this matters:**

When you use Pydantic to validate data, attempting to pass `None` for a non optional field will raise a validation
error:

```python exec="true" source="above" result="python" session="nullable-semantics"
# This works
user1 = User(name="Alice", email="alice@example.com")
user2 = User(name="Bob", email=None)  # email can be None

try:
    user3 = User(name=None, email="nobody@example.com")  # This raises ValidationError
except Exception as e:
    print(f"ValidationError: {type(e).__name__}")
```

The schema accurately reflects this constraint: `name` is not nullable, while `email` is nullable.

#### PyArrow schema generation with nullability

One powerful use case for explicit nullability is generating **PyArrow schemas with `not null` constraints**.
PyArrow (and many database systems) can distinguish between nullable and non-nullable columns, which provides:

* Data validation: Catch null values in supposedly non-nullable columns
* Performance optimizations: Some engines can optimize non-nullable columns
* Clear data contracts: Document which fields are guaranteed to have values

**Without anyschema** (default PyArrow behavior):

```python exec="true" source="above" result="python" session="pyarrow-nullability"
import pyarrow as pa
from pydantic import BaseModel


class User(BaseModel):
    name: str
    email: str | None


users = [
    User(name="Alice", email="alice@example.com"),
    User(name="Bob", email=None),
]

# PyArrow's default: both fields are nullable
default_table = pa.Table.from_pylist([user.model_dump() for user in users])
print("Default PyArrow schema:")
print(default_table.schema)
```

**With anyschema** (explicit nullability):

```python exec="true" source="above" result="python" session="pyarrow-nullability"
from anyschema import AnySchema

# Generate schema with explicit nullability from Pydantic model
anyschema_obj = AnySchema(spec=User)
arrow_schema = anyschema_obj.to_arrow()

# Create table with explicit schema
explicit_table = pa.Table.from_pylist(
    [user.model_dump() for user in users], schema=arrow_schema
)
print("anyschema-generated PyArrow schema:")
print(explicit_table.schema)
```

Notice that `name` is now marked as `not null` in the schema, accurately reflecting the type constraint from the
Pydantic model!

### `unique`

Specifies whether all values in the field must be unique.

* Applicable to: All field types
* Default: `False`
* Values: `True` or `False`

**Precedence rules** (highest to lowest):

1. Explicit `unique` metadata key
2. SQLAlchemy column `unique` property (auto-detected)
3. Default: `False`

!!! tip "SQLAlchemy Auto-Detection"
    For SQLAlchemy tables, the `unique` constraint is automatically detected from column properties.
    You can override this by explicitly setting `unique` in the column's `info` parameter.

Example:

```python exec="true" source="above" result="python" session="unique-example"
from pydantic import BaseModel, Field
from anyschema import AnySchema


class User(BaseModel):
    id: int = Field(json_schema_extra={"anyschema": {"unique": True}})
    username: str = Field(json_schema_extra={"anyschema": {"unique": True}})
    email: str


schema = AnySchema(spec=User)
print(f"id unique: {schema.fields['id'].unique}")
print(f"username unique: {schema.fields['username'].unique}")
print(f"email unique: {schema.fields['email'].unique}")
```

**Overriding SQLAlchemy unique constraint with explicit metadata:**

```python exec="true" source="above" result="python" session="unique-override"
from sqlalchemy import Column, Integer, MetaData, String, Table
from anyschema import AnySchema

metadata_obj = MetaData()
user_table = Table(
    "users",
    metadata_obj,
    Column("username", String(50), unique=True),  # SQLAlchemy unique=True
    # Override SQLAlchemy's unique with explicit metadata
    Column(
        "email",
        String(100),
        unique=True,  # SQLAlchemy says unique=True
        info={"anyschema": {"unique": False}},  # But metadata overrides to False
    ),
)

schema = AnySchema(spec=user_table)

print(f"username unique (from SQLAlchemy): {schema.fields['username'].unique}")
print(f"email unique (overridden by metadata): {schema.fields['email'].unique}")
```

### `description`

Provides a human-readable description of the field's purpose or content.

* Applicable to: All field types
* Default: `None`
* Values: Any string value

**Automatic extraction from:**

1. **Pydantic**: The `description` parameter of `Field()` is automatically extracted
2. **SQLAlchemy**: The `doc` parameter of `Column()` or `mapped_column()` is automatically extracted
3. **Dataclasses (Python 3.14+)**: The `doc` parameter of `field()` is automatically extracted
4. **Explicit metadata**: Set `{"anyschema": {"description": ...}}` in field metadata

Example with Pydantic:

```python exec="true" source="above" result="python" session="description-pydantic"
from pydantic import BaseModel, Field
from anyschema import AnySchema


class User(BaseModel):
    id: int = Field(description="Unique user identifier")
    username: str = Field(description="User's login name")
    email: str


schema = AnySchema(spec=User)
print(f"id description: {schema.fields['id'].description!r}")
print(f"username description: {schema.fields['username'].description!r}")
print(f"email description: {schema.fields['email'].description!r}")
```

Example with SQLAlchemy:

```python exec="true" source="above" result="python" session="description-sqlalchemy"
from sqlalchemy import Column, Integer, MetaData, String, Table
from anyschema import AnySchema

metadata_obj = MetaData()
user_table = Table(
    "users",
    metadata_obj,
    Column("id", Integer, primary_key=True, doc="Primary key identifier"),
    Column("username", String(50), doc="User's login name"),
    Column("email", String(100)),
)

schema = AnySchema(spec=user_table)

print(f"id description: {schema.fields['id'].description!r}")
print(f"username description: {schema.fields['username'].description!r}")
print(f"email description: {schema.fields['email'].description!r}")
```

Example with Dataclasses:

```python exec="true" source="above" result="python" session="description-dataclass"
from dataclasses import dataclass, field
from anyschema import AnySchema


@dataclass
class User:
    id: int = field(metadata={"anyschema": {"description": "Unique user identifier"}})
    username: str = field(metadata={"anyschema": {"description": "User's login name"}})
    email: str


schema = AnySchema(spec=User)
print(f"id description: {schema.fields['id'].description!r}")
print(f"username description: {schema.fields['username'].description!r}")
print(f"email description: {schema.fields['email'].description!r}")
```

### `time_zone`

Specifies the timezone for datetime fields as a string defined in `zoneinfo`.

To see valid values run `import zoneinfo; zoneinfo.available_timezones()` for the full list.

* Applicable to: `datetime` types and Pydantic datetime types.
* Default: `None` (no timezone, i.e., naive datetime)
* Resulting dtype: `nw.Datetime(time_zone = <time_zone value>)`

### `time_unit`

Specifies the time precision for datetime fields. Valid values are
`"s"` (seconds), `"ms"`(milliseconds),`"us"`(microseconds, default),`"ns"`(nanoseconds).

* Applicable to: `datetime` types and Pydantic datetime types
* Default: `"us"` (microseconds)
* Resulting dtype: `nw.Datetime(time_unit = <time_unit value>)`

### `dtype`

**Override** the automatically parsed dtype with a specific Narwhals dtype. This provides fine-grained control
over individual field dtypes without writing a custom parser.

* Applicable to: All field types
* Values: A `narwhals.dtypes.DType` instance or its string representation (e.g., `"String"`, `"List(Float64)"`)
* Behavior: **completely bypasses the parser pipeline** and uses the specified dtype directly

!!! warning "Pipeline Bypass"

    When you specify a `dtype` override, the parser pipeline is **completely bypassed** for that field.

    This means:

    * Type information (like `Optional[int]`) won't affect `nullable` unless explicitly set
    * Constraints and annotations are ignored
    * The specified dtype is used exactly as provided

    If you need nullable or other metadata, set them explicitly alongside `dtype`.

#### When to use `"anyschema": {"dtype": value}` vs custom parsers

* Use `dtype` override when you need to change the dtype for **specific fields** on a case-by-case basis.
* Use custom parsers when you want to change how a **type is always parsed** across your entire schema

See the [Custom Parsers vs dtype Override](#custom-parsers-vs-dtype-override) section below for a detailed comparison.

#### Example: Override with Narwhals DType

```python exec="true" source="above" result="python" session="dtype-override-narwhals"
from pydantic import BaseModel, Field
import narwhals as nw
from anyschema import AnySchema


class ProductWithOverrides(BaseModel):
    # Parse as String even though type hint is int
    product_id: int = Field(json_schema_extra={"anyschema": {"dtype": nw.String()}})

    # Parse as Int32 instead of default Int64
    quantity: int = Field(json_schema_extra={"anyschema": {"dtype": "Int32"}})

    # Without explicit nullable, Optional[int] won't make this nullable
    price: Optional[int] = Field(json_schema_extra={"anyschema": {"dtype": "UInt32"}})

    # Explicitly set nullable=True along with dtype override
    name: Optional[str] = Field(
        json_schema_extra={"anyschema": {"dtype": "String", "nullable": True}}
    )


schema = AnySchema(spec=ProductWithOverrides)
print(schema._nw_schema)
```

### Combining Multiple Metadata

You can specify multiple metadata keys for the same field:

```python exec="true" source="above" result="python" session="metadata-combined"
from datetime import datetime
from pydantic import BaseModel, Field
from anyschema import AnySchema


class LogEntry(BaseModel):
    message: str
    timestamp: datetime = Field(
        json_schema_extra={"anyschema": {"time_zone": "UTC", "time_unit": "ns"}}
    )


schema = AnySchema(spec=LogEntry)
print(schema._nw_schema)
```

## How to specify metadata

Different specification formats have their own ways of attaching metadata to fields.

Here's how to do it for each supported format.

### Pydantic Models

For Pydantic models, use the `json_schema_extra` parameter in `Field()`:

```python exec="true" source="above" result="python" session="metadata-pydantic"
from datetime import datetime
from pydantic import BaseModel, Field
from anyschema import AnySchema


class EventModel(BaseModel):
    name: str
    created_at: datetime  # Default datetime (no metadata)
    scheduled_at: datetime = Field(  # Specify timezone
        json_schema_extra={"anyschema": {"time_zone": "UTC"}}
    )
    started_at: datetime = Field(  # Specify time precision
        json_schema_extra={"anyschema": {"time_unit": "ms"}}
    )
    completed_at: datetime = Field(  # Specify both timezone and precision
        json_schema_extra={
            "anyschema": {"time_zone": "Europe/Berlin", "time_unit": "ns"}
        }
    )


schema = AnySchema(spec=EventModel)
print(schema._nw_schema)
```

#### Pydantic Special Datetime Types

When using Pydantic's special datetime types (`AwareDatetime`, `NaiveDatetime`), metadata is particularly useful:

```python exec="true" source="above" result="python" session="metadata-pydantic"
from pydantic import AwareDatetime, NaiveDatetime, Field


class TimeModel(BaseModel):
    aware_utc: AwareDatetime = Field(  # AwareDatetime **requires** timezone metadata
        json_schema_extra={"anyschema": {"time_zone": "UTC"}}
    )
    naive: NaiveDatetime = (
        Field(  # NaiveDatetime **rejects** timezone metadata (will raise an error)
            json_schema_extra={"anyschema": {"time_unit": "ns"}}
        )
    )


schema = AnySchema(spec=TimeModel)
print(schema._nw_schema)
```

!!! warning "AwareDatetime Requires Timezone"
    Pydantic's `AwareDatetime` type requires you to specify a timezone via `{"anyschema": {"time_zone": ...}}` metadata,
    otherwise anyschema will raise an `UnsupportedDTypeError`.

!!! warning "NaiveDatetime Cannot Have Timezone"
    Pydantic's `NaiveDatetime` type will raise an `UnsupportedDTypeError` if you specify a timezone in metadata.

### attrs Classes

For attrs classes, use the `metadata` parameter in `attrs.field()`:

```python exec="true" source="above" result="python" session="metadata-attrs"
from datetime import datetime
import attrs
from anyschema import AnySchema


@attrs.define
class EventModel:
    name: str
    created_at: datetime  # Default datetime (no metadata)
    scheduled_at: datetime = attrs.field(  # Specify timezone
        metadata={"anyschema": {"time_zone": "UTC"}}
    )
    started_at: datetime = attrs.field(  # Specify time precision
        metadata={"anyschema": {"time_unit": "ms"}}
    )
    completed_at: datetime = attrs.field(  # Specify both timezone and precision
        metadata={"anyschema": {"time_zone": "Europe/Berlin", "time_unit": "ns"}}
    )


schema = AnySchema(spec=EventModel)
print(schema._nw_schema)
```

This also works with `@attrs.frozen` classes:

```python exec="true" source="above" result="python" session="metadata-attrs"
@attrs.frozen
class ImmutableEvent:
    event_id: int
    timestamp: datetime = attrs.field(
        metadata={"anyschema": {"time_zone": "UTC", "time_unit": "ms"}}
    )


schema = AnySchema(spec=ImmutableEvent)
print(schema._nw_schema)
```

### Dataclasses

For standard Python dataclasses, use the `metadata` parameter in `field()`:

```python exec="true" source="above" result="python" session="metadata-dataclass"
from dataclasses import dataclass, field
from datetime import datetime
from anyschema import AnySchema


@dataclass
class EventModel:
    name: str
    created_at: datetime  # Default datetime (no metadata)
    scheduled_at: datetime = field(  # Specify timezone
        metadata={"anyschema": {"time_zone": "UTC"}}
    )
    started_at: datetime = field(  # Specify time precision
        metadata={"anyschema": {"time_unit": "ms"}}
    )
    completed_at: datetime = field(  # Specify both timezone and precision
        metadata={"anyschema": {"time_zone": "Europe/Berlin", "time_unit": "ns"}}
    )


schema = AnySchema(spec=EventModel)
print(schema._nw_schema)
```

This also works with Pydantic's dataclass decorator:

```python exec="true" source="above" result="python" session="metadata-dataclass"
from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass
class PydanticDataclassEvent:
    event_id: int
    timestamp: datetime = field(
        metadata={"anyschema": {"time_zone": "UTC", "time_unit": "ms"}}
    )


schema = AnySchema(spec=PydanticDataclassEvent)
print(schema._nw_schema)
```

### SQLAlchemy Tables

For SQLAlchemy tables and ORM models, use the `info` parameter in `Column()` or `mapped_column()`.

Additionally, SQLAlchemy automatically populates `nullable` and `unique` metadata based on
column properties:

```python exec="true" source="above" result="python" session="sqlalchemy-auto-metadata"
from sqlalchemy import Column, Integer, MetaData, String, Table
from anyschema import AnySchema

metadata = MetaData()

user_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, nullable=False),  # Not nullable
    Column("username", String(50), unique=True),  # Unique constraint
    Column("email", String(100), nullable=True),  # Explicitly nullable
    Column("bio", String(500)),  # Nullable by default
)

schema = AnySchema(spec=user_table)

print(schema.fields["id"])
print(schema.fields["username"])
print(schema.fields["email"])
print(schema.fields["bio"])
```

!!! info "SQLAlchemy DateTime Behavior"

    * Use `DateTime()` (or `DateTime(timezone=False)`) for naive datetimes.
        You can specify [`time_unit`](#time_unit) metadata but **not**
        [`time_zone`](#time_zone).
    * Use `DateTime(timezone=True)` for timezone-aware datetimes. You **must** specify
        [`time_zone`](#time_zone) metadata via the `info` parameter.

```python exec="true" source="above" result="python" session="metadata-sqlalchemy"
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table
from anyschema import AnySchema

metadata = MetaData()

event_table = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100)),
    Column("created_at", DateTime),  # Default datetime (no metadata)
    Column(
        "scheduled_at",
        DateTime(timezone=True),
        info={"anyschema": {"time_zone": "UTC"}},  # Specify timezone via info
    ),
    Column(
        "started_at",
        DateTime,
        info={"anyschema": {"time_unit": "ms"}},  # Specify time precision via info
    ),
    Column(
        "completed_at",
        DateTime(timezone=True),
        info={  # Specify both timezone and precision
            "anyschema": {"time_zone": "Europe/Berlin", "time_unit": "ns"}
        },
    ),
)

schema = AnySchema(spec=event_table)
print(schema._nw_schema)
```

This also works with SQLAlchemy ORM models using `mapped_column()`:

```python exec="true" source="above" result="python" session="metadata-sqlalchemy"
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EventORM(Base):
    __tablename__ = "event_orm"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    created_at: Mapped[DateTime] = mapped_column(DateTime)
    scheduled_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), info={"anyschema": {"time_zone": "UTC"}}
    )
    started_at: Mapped[DateTime] = mapped_column(
        DateTime, info={"anyschema": {"time_unit": "ms"}}
    )
    completed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        info={"anyschema": {"time_zone": "Europe/Berlin", "time_unit": "ns"}},
    )


schema = AnySchema(spec=EventORM)
print(schema._nw_schema)
```

#### SQLAlchemy Timezone-Aware DateTime

When using `DateTime(timezone=True)` in SQLAlchemy, you **must** specify a timezone via the `info` parameter:

```python exec="true" source="above" result="python" session="metadata-sqlalchemy"
event_table_tz = Table(
    "events_tz",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "timestamp_utc",
        DateTime(timezone=True),  # timezone=True requires time_zone in info
        info={"anyschema": {"time_zone": "UTC"}},
    ),
    Column(
        "timestamp_berlin",
        DateTime(timezone=True),
        info={"anyschema": {"time_zone": "Europe/Berlin", "time_unit": "ms"}},
    ),
)

schema = AnySchema(spec=event_table_tz)
print(schema._nw_schema)
```

!!! warning "DateTime(timezone=True) Requires Timezone"
    SQLAlchemy's `DateTime(timezone=True)` does not specify a fixed timezone value (it only indicates the database
    should store timezone information).

    You **must** specify a timezone via `info={'anyschema': {'time_zone': 'UTC'}}`, otherwise anyschema will raise an
    `UnsupportedDTypeError`.

!!! warning "DateTime() Cannot Have Timezone with timezone=False"
    SQLAlchemy's `DateTime()` or `DateTime(timezone=False)` is for naive datetimes and will raise an
    `UnsupportedDTypeError` if you specify a timezone in the `info` parameter.

### TypedDict

!!! info "TypedDict Limitation"
    TypedDict classes do not support field metadata at the type annotation level.
    If you need to specify metadata for TypedDict fields, consider using dataclasses, Pydantic models, or attrs classes
    instead.

## Custom Metadata

While anyschema recognizes the special `"anyschema"` key (and its OpenAPI variant `"x-anyschema"`), you can also
include custom metadata for your own purposes. This metadata will be passed to custom parser steps, allowing you to
implement domain-specific parsing logic.

For example:

```python
from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str = Field(
        json_schema_extra={
            "anyschema": {"time_zone": "UTC"},  # Recognized by anyschema
            "my_app/description": "Product name",  # Custom metadata
            "my_app/max_length": 100,  # Custom metadata
        }
    )
```

To handle custom metadata, you would need to implement a custom parser step.

See the [Advanced Usage](advanced.md#custom-parser-with-metadata-handling) guide for more information on creating
custom parsers that process metadata.

## Custom parsers vs `dtype` override

Both custom parsers and the `dtype` metadata override allow you to control how types are converted to Narwhals dtypes,
but they serve different purposes and work at different levels.

**Custom parser approach** characteristics:

* Global scope: Affects all fields with the specified type across your entire schema
* Runs in pipeline: Integrated into the parser pipeline, respects order and precedence
* Reusable: Define once, applies to all schemas using that pipeline
* Type-driven: Makes decisions based on types, constraints and metadata
* Composable: Can be combined with other parsers in the pipeline

**`dtype` override approach** characteristics:

* Field-specific: Affects only the individual field where it's specified
* Bypasses pipeline: Completely skips type parsing for that field
* Declarative: Specified in field metadata, not in parser code
* Granular control: Different fields with the same type can have different dtypes
* Configuration-friendly: Can be stored in config files, database schemas, etc.

It's entirely possible to combine both approaches: you can use both custom parsers and dtype overrides together.

The dtype override takes precedence:

```python exec="true" source="above" result="python" session="combined-example"
from pydantic import BaseModel, Field
import narwhals as nw
from anyschema import AnySchema
from anyschema.parsers import ParserStep, ParserPipeline
from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


class Int32ParserStep(ParserStep):
    """Default all int to Int32."""

    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> nw.DType | None:
        return nw.Int32() if input_type is int else None


class Product(BaseModel):
    id: int  # Will use custom parser
    quantity: int = Field(
        json_schema_extra={"anyschema": {"dtype": "Int16"}}
    )  # Override to Int16
    stock: int  # Will use custom parser
    name: str  # Parsed normally


pipeline = ParserPipeline.from_auto(steps=[Int32ParserStep()])
schema = AnySchema(spec=Product, pipeline=pipeline)

print("Combined approach:")
for field_name, field in schema.fields.items():
    print(f"  {field_name}: {field.dtype}")
```

In this example:

* `id` and `stock` use the custom parser -> `Int32`
* `quantity` uses dtype override -> `Int16` (override takes precedence)
* `name` uses standard parsing -> `String`
