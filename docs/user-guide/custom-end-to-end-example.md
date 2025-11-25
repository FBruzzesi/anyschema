
# Custom End to End Example

Let's now combine the learnings from the [previous section](advanced.md) to show an example that combines a custom
parser and a custom adapter.

## 1. Define custom types

```python exec="true" source="above" session="end-to-end"
from typing import Any

import narwhals as nw
from narwhals.dtypes import DType

from anyschema import AnySchema
from anyschema.parsers import (
    ParserStep,
    ForwardRefStep,
    UnionTypeStep,
    AnnotatedStep,
    PyTypeStep,
    make_pipeline,
)
from anyschema.typing import FieldSpecIterable


class Email:
    """Email address type."""


class PhoneNumber:
    """Phone number type."""


class Currency:
    """Monetary value type."""
```

## 2. Create custom parser for these such types

```python exec="true" source="above" session="end-to-end"
class CustomerTypesStep(ParserStep):
    """Parser for custom types."""

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        if input_type is Email:
            return nw.String()
        elif input_type is PhoneNumber:
            return nw.String()
        elif input_type is Currency:
            return nw.Float32()
        return None
```

## 3. Define custom schema format

```python exec="true" source="above" session="end-to-end"
class CustomerSchema:
    """Custom schema format."""

    def __init__(self, entity_name: str, fields: list[dict]):
        self.entity_name = entity_name
        self.fields = fields
```

## 4. Create adapter for the custom format

```python exec="true" source="above" session="end-to-end"
def customer_schema_adapter(spec: CustomerSchema) -> FieldSpecIterable:
    """Adapter for CustomerSchema format."""
    for field in spec.fields:
        field_name = field["name"]
        field_type = field["type"]
        required = field.get("required", True)

        # Convert required=False to Optional
        if not required:
            field_type = field_type | None

        yield field_name, field_type, ()
```

## 5. Create pipeline steps with custom parser

```python exec="true" source="above" session="end-to-end"
pipeline_steps = [
    ForwardRefStep(),
    UnionTypeStep(),
    AnnotatedStep(),
    CustomerTypesStep(),
    PyTypeStep(),
]
```

## 6. Use everything together

```python exec="true" source="above" result="python" session="end-to-end"
customer_schema = CustomerSchema(
    entity_name="Customer",
    fields=[
        {"name": "id", "type": int, "required": True},
        {"name": "name", "type": str, "required": True},
        {"name": "email", "type": Email, "required": True},
        {"name": "phone", "type": PhoneNumber, "required": False},
        {"name": "balance", "type": Currency, "required": True},
    ],
)

schema = AnySchema(
    spec=customer_schema,
    steps=pipeline_steps,
    adapter=customer_schema_adapter,
)

print(schema.to_polars())
```
