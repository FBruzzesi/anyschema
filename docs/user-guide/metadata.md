# Metadata

Metadata allows you to provide additional information about fields that influences how they are parsed into
dataframe schemas.

This guide covers how to specify metadata for different specification formats and which metadata keys have special
behavior in `anyschema`.

## Overview

Metadata is a dictionary of key-value pairs attached to individual fields.
While you can store any custom metadata, anyschema recognizes a special nested dictionary under the
`"__anyschema_metadata__"` key that modifies parsing behavior.

Currently supported anyschema metadata keys (nested under `"__anyschema_metadata__"`):

* `"nullable"`: Specifies whether the field can contain null values.
* `"unique"`: Specifies whether all values in the field must be unique.
* `"description"`: Provides a human-readable description of the field.
* `"time_zone"`: Specifies timezone for datetime fields.
* `"time_unit"`: Specifies time precision for datetime fields (default: `"us"`).

## The `AnyField` Class

Starting from version 0.3.0, `anyschema` provides a [`AnyField`][anyschema.AnyField] class that encapsulates detailed
information about each field in a schema.

When you create an `AnySchema`, it parses each field into a `AnyField` object that contains:

* `name`: The field name
* `dtype`: The Narwhals data type
* `nullable`: Whether the field accepts null values
* `unique`: Whether values must be unique
* `description`: Human-readable field description
* `metadata`: Custom metadata dictionary (excluding `__anyschema_metadata__` dict)

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
    Explicit anyschema metadata keys **always take precedence** over values inferred from types.

    For example, setting `nullable: False` in `__anyschema_metadata__` will make a field non-nullable even if the type
    is `Optional[T]`. This allows you to override type-level inference when needed.

### `nullable`

Specifies whether the field can contain null values.

**Precedence rules** (highest to lowest):

1. Explicit `nullable` key in `__anyschema_metadata__`
2. Type inference (`Optional[T]` or `T | None`)
3. Default: `False` (non-nullable by default)

Example:

```python exec="true" source="above" result="python" session="nullable-example"
from pydantic import BaseModel, Field
from anyschema import AnySchema


class User(BaseModel):
    id: int = Field(json_schema_extra={"__anyschema_metadata__": {"nullable": False}})
    username: str
    email: str | None


schema = AnySchema(spec=User)

print(f"id nullable (explicit metadata): {schema.fields['id'].nullable}")
print(f"username nullable (default): {schema.fields['username'].nullable}")
print(f"email nullable (type inference): {schema.fields['email'].nullable}")
```

**Overriding type inference with explicit metadata:**

```python exec="true" source="above" result="python" session="nullable-override"
from typing import Optional
from pydantic import BaseModel, Field
from anyschema import AnySchema


class Config(BaseModel):
    # Type says Optional, but metadata overrides to non-nullable
    required_field: Optional[str] = Field(
        json_schema_extra={"__anyschema_metadata__": {"nullable": False}}
    )
    # Type says non-Optional, but metadata overrides to nullable
    optional_field: str = Field(
        json_schema_extra={"__anyschema_metadata__": {"nullable": True}}
    )


schema = AnySchema(spec=Config)

print("required_field", schema.fields["required_field"].nullable)
print("optional_field", schema.fields["optional_field"].nullable)
```

### `unique`

Specifies whether all values in the field must be unique.

* Applicable to: All field types
* Default: `False`
* Values: `True` or `False`

**Precedence rules** (highest to lowest):

1. Explicit `unique` key in `__anyschema_metadata__`
2. SQLAlchemy column `unique` property (auto-detected)
3. Default: `False`

!!! tip "SQLAlchemy Auto-Detection"
    For SQLAlchemy tables, the `unique` constraint is automatically detected from column properties.
    You can override this by explicitly setting `unique` in the column's `info` parameter under
    `__anyschema_metadata__`.

Example:

```python exec="true" source="above" result="python" session="unique-example"
from pydantic import BaseModel, Field
from anyschema import AnySchema


class User(BaseModel):
    id: int = Field(json_schema_extra={"__anyschema_metadata__": {"unique": True}})
    username: str = Field(
        json_schema_extra={"__anyschema_metadata__": {"unique": True}}
    )
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
        info={
            "__anyschema_metadata__": {"unique": False}
        },  # But metadata overrides to False
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
4. **Explicit metadata**: Set `"description"` in the `__anyschema_metadata__` dict

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
    id: int = field(
        metadata={"__anyschema_metadata__": {"description": "Unique user identifier"}}
    )
    username: str = field(
        metadata={"__anyschema_metadata__": {"description": "User's login name"}}
    )
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

### Combining Multiple Metadata

You can specify multiple metadata keys for the same field:

```python exec="true" source="above" result="python" session="metadata-combined"
from datetime import datetime
from pydantic import BaseModel, Field
from anyschema import AnySchema


class LogEntry(BaseModel):
    message: str
    timestamp: datetime = Field(
        json_schema_extra={
            "__anyschema_metadata__": {"time_zone": "UTC", "time_unit": "ns"}
        }
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
        json_schema_extra={"__anyschema_metadata__": {"time_zone": "UTC"}}
    )
    started_at: datetime = Field(  # Specify time precision
        json_schema_extra={"__anyschema_metadata__": {"time_unit": "ms"}}
    )
    completed_at: datetime = Field(  # Specify both timezone and precision
        json_schema_extra={
            "__anyschema_metadata__": {
                "time_zone": "Europe/Berlin",
                "time_unit": "ns",
            }
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
        json_schema_extra={"__anyschema_metadata__": {"time_zone": "UTC"}}
    )
    naive: NaiveDatetime = (
        Field(  # NaiveDatetime **rejects** timezone metadata (will raise an error)
            json_schema_extra={"__anyschema_metadata__": {"time_unit": "ns"}}
        )
    )


schema = AnySchema(spec=TimeModel)
print(schema._nw_schema)
```

!!! warning "AwareDatetime Requires Timezone"
    Pydantic's `AwareDatetime` type requires you to specify a timezone via `"time_zone"` in `__anyschema_metadata__`,
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
        metadata={"__anyschema_metadata__": {"time_zone": "UTC"}}
    )
    started_at: datetime = attrs.field(  # Specify time precision
        metadata={"__anyschema_metadata__": {"time_unit": "ms"}}
    )
    completed_at: datetime = attrs.field(  # Specify both timezone and precision
        metadata={
            "__anyschema_metadata__": {"time_zone": "Europe/Berlin", "time_unit": "ns"}
        }
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
        metadata={"__anyschema_metadata__": {"time_zone": "UTC", "time_unit": "ms"}}
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
        metadata={"__anyschema_metadata__": {"time_zone": "UTC"}}
    )
    started_at: datetime = field(  # Specify time precision
        metadata={"__anyschema_metadata__": {"time_unit": "ms"}}
    )
    completed_at: datetime = field(  # Specify both timezone and precision
        metadata={
            "__anyschema_metadata__": {"time_zone": "Europe/Berlin", "time_unit": "ns"}
        }
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
        metadata={"__anyschema_metadata__": {"time_zone": "UTC", "time_unit": "ms"}}
    )


schema = AnySchema(spec=PydanticDataclassEvent)
print(schema._nw_schema)
```

### SQLAlchemy Tables

For SQLAlchemy tables and ORM models, use the `info` parameter in `Column()` or `mapped_column()`.

Additionally, SQLAlchemy automatically populates `nullable` and `unique` in the `__anyschema_metadata__` dict based on
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
        [`time_zone`](#time_zone) metadata via the `info` parameter in `__anyschema_metadata__`.

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
        info={
            "__anyschema_metadata__": {"time_zone": "UTC"}
        },  # Specify timezone via info
    ),
    Column(
        "started_at",
        DateTime,
        info={
            "__anyschema_metadata__": {"time_unit": "ms"}
        },  # Specify time precision via info
    ),
    Column(
        "completed_at",
        DateTime(timezone=True),
        info={  # Specify both timezone and precision
            "__anyschema_metadata__": {
                "time_zone": "Europe/Berlin",
                "time_unit": "ns",
            }
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
        DateTime(timezone=True), info={"__anyschema_metadata__": {"time_zone": "UTC"}}
    )
    started_at: Mapped[DateTime] = mapped_column(
        DateTime, info={"__anyschema_metadata__": {"time_unit": "ms"}}
    )
    completed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        info={
            "__anyschema_metadata__": {"time_zone": "Europe/Berlin", "time_unit": "ns"}
        },
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
        info={"__anyschema_metadata__": {"time_zone": "UTC"}},
    ),
    Column(
        "timestamp_berlin",
        DateTime(timezone=True),
        info={
            "__anyschema_metadata__": {"time_zone": "Europe/Berlin", "time_unit": "ms"}
        },
    ),
)

schema = AnySchema(spec=event_table_tz)
print(schema._nw_schema)
```

!!! warning "DateTime(timezone=True) Requires Timezone"
    SQLAlchemy's `DateTime(timezone=True)` does not specify a fixed timezone value (it only indicates the database
    should store timezone information).

    You **must** specify a timezone via `info={'__anyschema_metadata__': {'time_zone': 'UTC'}}`,
    otherwise anyschema will raise an `UnsupportedDTypeError`.

!!! warning "DateTime() Cannot Have Timezone with timezone=False"
    SQLAlchemy's `DateTime()` or `DateTime(timezone=False)` is for naive datetimes and will raise an
    `UnsupportedDTypeError` if you specify a timezone in the `__anyschema_metadata__` dict in the `info` parameter.

### TypedDict

!!! info "TypedDict Limitation"
    TypedDict classes do not support field metadata at the type annotation level.
    If you need to specify metadata for TypedDict fields, consider using dataclasses, Pydantic models, or attrs classes
    instead.

## Custom Metadata

While anyschema recognizes the special `"__anyschema_metadata__"` dict, you can also include custom
metadata for your own purposes.
This metadata will be passed to custom parser steps, allowing you to implement domain-specific parsing logic.

For example:

```python
from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str = Field(
        json_schema_extra={
            "__anyschema_metadata__": {"time_zone": "UTC"},  # Recognized by anyschema
            "my_app/description": "Product name",  # Custom metadata
            "my_app/max_length": 100,  # Custom metadata
        }
    )
```

To handle custom metadata, you would need to implement a custom parser step.

See the [Advanced Usage](advanced.md#custom-parser-with-metadata-handling) guide for more information on creating
custom parsers that process metadata.
