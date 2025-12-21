# Troubleshooting

This page covers common issues you might encounter when using anyschema and how to resolve them.

## Common Issues

### Type Not Supported

If you are prompted the following error message:

> NotImplementedError: No parser in the pipeline could handle type: 'type-name'

it means that the type you're trying to convert isn't handled by any parser in the pipeline.

The solution is to implement a [custom parser step](advanced.md#custom-parser-steps) and adding it to the pipeline
steps:

```python
from typing import Any
import narwhals as nw

from anyschema import AnySchema
from anyschema.parsers import ParserStep, PyTypeStep
from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


class MyCustomTypeStep(ParserStep):
    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> nw.dtypes.DType | None:
        if input_type is MyCustomType:
            return nw.String()  # or appropriate dtype
        return None


schema = AnySchema(spec=your_spec, pipeline=[MyCustomTypeStep(), PyTypeStep()])
```

### Union Type Error

If you are prompted the following error message:

> UnsupportedDTypeError: Union with mixed types is not supported.

it means that the dataframe libraries don't support true union types.
`Optional[T]` (i.e., `T | None`) is supported, however true union types such as `float | str` are not.

### Custom Parser Not Being Called

There could be multiple reasons why your custom parser's `parse` method never gets invoked.

One reason might be that the order in step sequence is wrong.

Parser steps are tried in order. If an earlier parser handles the type, yours won't be called.

```python
# ❌ PyTypeStep catches everything before CustomStep runs
steps = [PyTypeStep(), CustomStep()]

# ✅ Place custom parsers before general ones
steps = [CustomStep(), PyTypeStep()]
```

Another reason might be that the step is not registered: make sure you pass the parser to `AnySchema`:

```python
# ✅ Explicitly provide steps
schema = AnySchema(spec=spec, pipeline=[CustomStep(), PyTypeStep()])
```

### Metadata Not Flowing Through

If your parser steps expects metadata, yet it receives empty metadata, then make sure to include `AnnotatedStep` in the
pipeline:

```python
from anyschema.parsers import AnnotatedStep
from anyschema.typing import FieldConstraints, FieldMetadata, FieldType

steps = (
    AnnotatedStep(),  # Must be present to extract metadata
    YourCustomStep(),
    PyTypeStep(),
)
```

On top of that, verify metadata are preserved when recursively parsing:

```python
class CustomStep(ParserStep):
    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,
    ) -> nw.dtypes.DType | None:
        inner_type = get_args(input_type)[0]
        # ✅ Pass constraints and metadata through
        return self.pipeline.parse(
            inner_type, constraints=constraints, metadata=metadata
        )
```

### Adapter Not Processing Nested Structures

If nested specification are not being converted correctly, we suggest to "hack" using `TypedDict`'s when adapting nested
schemas:

```python
from typing import TypedDict
from anyschema.typing import FieldSpecIterable


def my_adapter(spec: MySchema) -> FieldSpecIterable:
    for field_name, field_value in spec.fields.items():
        if is_nested(field_value):
            # Create a TypedDict for nested structures
            nested_dict = {name: type_ for name, type_, _, _ in my_adapter(field_value)}
            nested_typed_dict = TypedDict(f"{field_name.title()}Schema", nested_dict)
            yield field_name, nested_typed_dict, (), {}
        else:
            yield field_name, field_value, (), {}
```

In general, make sure your adapter recursively processes nested structures.

See the [Advanced Usage - Adapter for Nested Structures](advanced.md#adapter-for-nested-structures) for a complete
example.

### Why are all my fields nullable in `pyarrow`?

If you're creating PyArrow tables without passing a schema, all fields will be nullable by default (this is PyArrow's
standard behavior):

```python exec="true" source="above" result="python" session="troubleshoot-nullable"
import pyarrow as pa
from pydantic import BaseModel


class User(BaseModel):
    id: int  # Non-nullable in Pydantic
    name: str  # Non-nullable in Pydantic
    email: str | None  # Nullable


users = [{"id": 1, "name": "Alice", "email": "alice@example.com"}]

# Without schema: everything is nullable
table = pa.Table.from_pylist(users)
print("Without explicit schema:")
print(table.schema)
```

**Solution**: Use `anyschema` to generate a schema that preserves nullability information:

```python exec="true" source="above" result="python" session="troubleshoot-nullable"
from anyschema import AnySchema

schema = AnySchema(spec=User)
arrow_schema = schema.to_arrow()

# With schema: nullability matches type annotations
table_with_schema = pa.Table.from_pylist(users, schema=arrow_schema)
print("With anyschema-generated schema:")
print(table_with_schema.schema)
```

Now `id` and `name` are correctly marked as `not null`!

See the [Metadata guide on nullable semantics](metadata.md#understanding-nullable-semantics) for more details.

### Field shows as nullable when it shouldn't be

If a field appears nullable but your type annotations say it's not nullable, check:

1. **Type annotation is correct**: Use `str`, not `str | None` or `Optional[str]`
2. **Not overridden by metadata**: Check if `"anyschema": {"nullable": True}` was set in metadata

```python exec="true" source="above" result="python" session="troubleshoot-not-nullable"
from pydantic import BaseModel, Field
from anyschema import AnySchema


class Example(BaseModel):
    # This WILL be nullable despite the type annotation
    field: str = Field(json_schema_extra={"anyschema": {"nullable": True}})


schema = AnySchema(spec=Example)
print(f"field is nullable: {schema.fields['field'].nullable}")
```

Explicit metadata always takes precedence over type inference.

## Getting Help

If you're still stuck after trying these solutions:

1. Check existing issues: Search the [GitHub issue tracker](https://github.com/FBruzzesi/anyschema/issues) for similar problems.
2. Create a minimal reproduction: Prepare a minimal code example that demonstrates the issue

    ```python
    from anyschema import AnySchema
    from pydantic import BaseModel


    class MinimalExample(BaseModel):
        field: YourProblematicType


    schema = AnySchema(spec=MinimalExample)
    # Error occurs here
    # ...

    arrow_schema = schema.to_arrow()
    ```

3. Open an issue and make sure to include:

    * Your Python and anyschema versions
    * The minimal reproduction code
    * The full error traceback
    * What you've already tried
