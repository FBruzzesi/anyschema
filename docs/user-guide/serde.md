# Serialization & Deserialization

The [`anyschema.serde`][serde-api] module provides utilities to serialize and deserialize Narwhals dtypes to and from
string representations.

This is essential when you need to store, transmit, or share schema information in JSON-compatible formats.

## Overview

Two main functions are available:

* `serialize_dtype(dtype: DType) -> str`: Converts a Narwhals dtype to its string representation.
* `deserialize_dtype(into_dtype: str) -> DType`: Reconstructs a Narwhals dtype from a string.

These functions support all Narwhals dtypes, including complex nested structures like `List`, `Struct`, and `Array`.

## Why Serialization Matters

Serialization enables you to:

* Store schemas in databases or configuration files as JSON
* Transmit schemas via APIs or network requests
* Share schemas across different services or programming languages
* Document types explicitly in JSON schemas beyond Python's type system
* Version control schema definitions in human-readable formats

## Basic Usage

### Simple Types

Converting basic Narwhals dtypes to strings and back:

```python exec="true" source="above" result="python" session="serde-basic"
import narwhals as nw
from anyschema.serde import serialize_dtype, deserialize_dtype


dtype = nw.Int64()

# Serialize a dtype to string
dtype_str = serialize_dtype(dtype)
print(f"Serialized: {dtype_str}")

# Deserialize back to dtype
reconstructed = deserialize_dtype(dtype_str)
print(f"Deserialized: {reconstructed}")
print(f"Round-trip successful: {dtype == reconstructed}")
```

### Nested Types

Serde handles nested and complex types seamlessly:

```python exec="true" source="above" result="python" session="serde-nested"
import narwhals as nw
from anyschema.serde import serialize_dtype, deserialize_dtype


# Complex nested structure
complex_dtype = nw.Struct(
    {
        "id": nw.Int64(),
        "tags": nw.List(nw.String()),
        "metadata": nw.Struct(
            {
                "created": nw.Datetime(time_unit="ms", time_zone="UTC"),
                "active": nw.Boolean(),
            }
        ),
    }
)

# Serialize
dtype_str = serialize_dtype(complex_dtype)
print(f"Serialized:\n{dtype_str}")

# Deserialize
reconstructed = deserialize_dtype(dtype_str)
print(f"\nDeserialized: {reconstructed}")
print(f"Round-trip successful: {complex_dtype == reconstructed}")
```

## Integration with Pydantic

A common use case is storing Narwhals dtype information in Pydantic model JSON schemas.
This allows you to specify precise type information beyond what Python's type system provides.

### The Challenge

Pydantic's `json_schema_extra` parameter must contain JSON-serializable values.
Since Narwhals dtype objects are not JSON-serializable, it's necessary to **pre-serialize** them at field definition
time.

!!! warning "Important: Pre-serialization Required"
    Pydantic processes `json_schema_extra` during Field initialization, **before** any custom schema generators run.

    This means you cannot use a custom `GenerateJsonSchema` to automatically serialize Narwhals dtypes.

    You must serialize them explicitly.

### Helper Class

Create a helper class to make serialization convenient:

```python exec="true" source="above" session="serde-pydantic"
from typing import Any

import narwhals as nw
from anyschema.serde import serialize_dtype, deserialize_dtype


class NarwhalsTypeSerializer:
    """Helper to serialize/deserialize Narwhals dtypes."""

    @staticmethod
    def serialize(dtype: Any) -> str | Any:
        """Convert Narwhals dtype to string, pass through other values."""
        return serialize_dtype(dtype) if isinstance(dtype, nw.dtypes.DType) else dtype

    @staticmethod
    def deserialize(into_dtype: str) -> nw.dtypes.DType:
        """Convert string back to Narwhals dtype, pass through values that cannot be converted."""
        dtype = deserialize_dtype(into_dtype)
        return into_dtype if dtype is nw.Unknown() else dtype
```

### Basic Example

Store dtype information alongside Pydantic fields:

```python exec="true" source="above" result="python" session="serde-pydantic"
import json
from datetime import datetime
from pydantic import BaseModel, Field


class UserModel(BaseModel):
    """User model with Narwhals dtype metadata."""

    user_id: int = Field(
        description="Unique user identifier",
        json_schema_extra={
            "anyschema": {
                "dtype": NarwhalsTypeSerializer.serialize(nw.UInt64()),
            },
        },
    )

    username: str = Field(
        description="Username",
        json_schema_extra={
            "anyschema": {
                "dtype": NarwhalsTypeSerializer.serialize(nw.String()),
            }
        },
    )

    created_at: datetime = Field(
        description="Account creation timestamp",
        json_schema_extra={
            "anyschema": {
                "dtype": NarwhalsTypeSerializer.serialize(
                    nw.Datetime(time_unit="ms", time_zone="UTC")
                ),
            }
        },
    )


# Generate JSON schema
json_schema = UserModel.model_json_schema()
for field_name in UserModel.model_fields:
    dtype = json.dumps(json_schema["properties"][field_name]["anyschema"]["dtype"])
    print(f"{field_name} dtype is {dtype}")
```

### Complex Field Types

Serde works with complex nested types in Pydantic models:

```python exec="true" source="above" result="python" session="serde-pydantic"
import json
import narwhals as nw
from anyschema.serde import serialize_dtype, deserialize_dtype
from pydantic import BaseModel, Field


class DataModel(BaseModel):
    """Model with complex nested dtypes."""

    tags: list[str] = Field(
        description="List of tags",
        json_schema_extra={
            "anyschema": {"dtype": serialize_dtype(nw.List(nw.String()))}
        },
    )

    metadata: dict = Field(
        description="Structured metadata",
        json_schema_extra={
            "anyschema": {
                "dtype": serialize_dtype(
                    nw.Struct(
                        {"id": nw.Int64(), "name": nw.String(), "active": nw.Boolean()}
                    )
                )
            }
        },
    )

    matrix: list[list[float]] = Field(
        description="2D array",
        json_schema_extra={
            "anyschema": {
                "dtype": serialize_dtype(nw.Array(nw.Float32(), shape=(3, 2)))
            }
        },
    )


json_schema = DataModel.model_json_schema()
for field_name in DataModel.model_fields:
    dtype = json.dumps(json_schema["properties"][field_name]["anyschema"]["dtype"])
    print(f"{field_name} dtype is {dtype}")
```

## Deserialize dtypes from json schema

### Manual deserialization

Extract and deserialize dtypes from the JSON schema:

```python exec="true" source="above" result="python" session="serde-pydantic"
json_schema = UserModel.model_json_schema()

print("Field dtypes from JSON schema:")
for field_name, field_info in json_schema["properties"].items():
    if into_dtype := field_info.get("anyschema", {}).get("dtype"):
        dtype = NarwhalsTypeSerializer.deserialize(into_dtype)
        print(f"\t* {field_name}: {dtype}")
```

### Custom JSON Decoder

For more sophisticated workflows, create custom JSON encoder/decoder classes that automatically handle Narwhals dtypes:

```python exec="true" source="above" result="python" session="serde-decoder"
from contextlib import suppress
import json
import narwhals as nw
from anyschema.exceptions import UnsupportedDTypeError
from anyschema.serde import serialize_dtype, deserialize_dtype


class NarwhalsDTypeEncoder(json.JSONEncoder):
    """JSON encoder that automatically serializes Narwhals dtypes."""

    def default(self, obj):
        if isinstance(obj, nw.dtypes.DType):
            # Return a dict with a special marker
            return serialize_dtype(obj)
        return super().default(obj)


class NarwhalsDTypeDecoder(json.JSONDecoder):
    """JSON decoder that automatically deserializes Narwhals dtypes."""

    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    @staticmethod
    def object_hook(obj):
        """Hook to intercept dict objects during decoding."""
        if isinstance((into_dtype := obj.get("dtype")), str):
            with suppress(UnsupportedDTypeError):
                dtype = deserialize_dtype(into_dtype)
                obj["dtype"] = dtype

        return obj


# Example: Store arbitrary data with Narwhals dtypes
data = {
    "schema_version": "1.0",
    "fields": {
        "id": {
            "dtype": nw.UInt64(),
            "nullable": False,
        },
        "tags": {
            "dtype": nw.List(nw.String()),
            "nullable": True,
        },
        "unknown": {"dtype": "not a narwhals object", "nullable": "Maybe!"},
    },
}

# Encode with custom encoder
json_str = json.dumps(data, cls=NarwhalsDTypeEncoder, indent=2)
print("Encoded JSON")
print(json_str)

# Decode with custom decoder
loaded_data = json.loads(json_str, cls=NarwhalsDTypeDecoder)

print("\nDecoded dtypes:")
for field_name, field_info in loaded_data["fields"].items():
    dtype = field_info["dtype"]
    print(f"  {field_name}: {dtype} (type: {type(dtype).__name__})")
```

[serde-api]: ../api-reference/serde.md
