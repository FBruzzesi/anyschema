# Spec Adapters

Adapters convert various input specifications into a normalized format for parsing.

Learn how to create custom adapters in the [Advanced Usage](../user-guide/advanced.md#custom-spec-adapters) guide.

The following built-in adapters are not meant to be used directly. They serve more as an example than anything else.

::: anyschema.adapters
    handler: python
    options:
      show_root_heading: true
      show_source: true

## Adapters specification

Adapters must follow this signature:

```python
from typing import Iterator, TypeAlias, Callable, Any, Generator
from anyschema.typing import FieldConstraints, FieldMetadata, FieldName, FieldType

FieldSpec: TypeAlias = tuple[FieldName, FieldType, FieldConstraints, FieldMetadata]


def my_custom_adapter(spec: Any) -> Iterator[FieldSpec]:
    """
    Yields tuples of (field_name, field_type, constraints, metadata).

    - name (str): The name of the field
    - type (type): The type annotation of the field
    - constraints (tuple): Type constraints (e.g., Gt(0), Le(100) from annotated-types)
    - metadata (dict): Custom metadata dictionary for additional information
    """
    ...
```

They don't need to be functions; any callable is acceptable.
