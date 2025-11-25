# Spec Adapters

Adapters convert various input specifications into a normalized format for parsing.

Learn how to create custom adapters in the [Advanced Usage](../user-guide/advanced.md#custom-spec-adapters) guide.

The following built-in adapters are not meant to be used directly. They serve more as an example than anything else.

::: anyschema.adapters.into_ordered_dict_adapter
    handler: python
    options:
      show_root_heading: true
      show_source: true

::: anyschema.adapters.pydantic_adapter
    handler: python
    options:
      show_root_heading: true
      show_source: true

## Adapters specification

Adapters must follow this signature:

```python
from typing import Iterator, TypeAlias, Callable, Any, Generator
from anyschema.typing import FieldMetadata, FieldName, FieldType

FieldSpec: TypeAlias = tuple[FieldName, FieldType, FieldMetadata]


def my_custom_adapter(spec: Any) -> Iterator[FieldSpec]:
    ...
```

They don't need to be functions; any callable is acceptable.
