# Spec Adapters

Adapters convert various input specifications into a normalized format for parsing.

Learn how to create custom adapters in the [Advanced Usage](../user-guide/advanced.md#custom-spec-adapters) guide.

The following built-in adapters are not meant to be used directly. They serve more as an example than anything else.

::: anyschema.adapters
    handler: python
    options:
      show_root_heading: true
      show_source: true
    members:
      - dataclass_adapter
      - into_ordered_dict_adapter
      - pydantic_adapter

## Adapters specification

Adapters must follow this signature:

```python
from anyschema.typing import Adapter, FieldSpecIterable


def my_custom_adapter(spec: MyCustomType) -> FieldSpecIterable:
    """Adapter for MyCustomType.

    Arguments:
        spec: The custom specification to adapt.

    Yields:
        Tuples of (field_name, field_type, metadata) for each field.
    """
    for field_name, field_type in spec.fields.items():
        yield field_name, field_type, ()
```

The `Adapter` type is a generic Protocol that accepts a spec of type `T` and returns a `FieldSpecIterable`.
This provides better type safety when creating custom adapters.

**Type Signature:**

```python
from typing import Protocol, TypeVar

SpecT_contra = TypeVar("SpecT_contra", contravariant=True)


class Adapter(Protocol[SpecT_contra]):
    def __call__(self, spec: SpecT_contra, /) -> FieldSpecIterable:
        ...
```

Adapters don't need to be functions; any callable matching this signature is acceptable.
