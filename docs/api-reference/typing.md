
# Type Aliases

The following type aliases are used throughout the anyschema codebase:

## Spec

The `Spec` type represents valid input specifications:

```python
Spec = Union[
    Schema,  # Narwhals Schema
    type[BaseModel],  # Pydantic model class
    Mapping[str, type],  # Dict of field_name -> type
    Sequence[tuple[str, type]],  # List of (field_name, type) tuples
]
```

## IntoParserPipeline

The `IntoParserPipeline` type represents valid parser pipeline specifications:

```python
IntoParserPipeline = Union[
    Literal["auto"],  # Automatic parser selection
    Sequence[ParserStep],  # Custom sequence of parser steps
]
```

## Adapter

The `Adapter` type represents a function that adapts a spec into field specifications:

```python
Adapter = Callable[[Any], Iterator[tuple[str, type, tuple]]]
```

Each adapter yields tuples of:

- `field_name` (str): The name of the field
- `field_type` (type): The type annotation of the field
- `metadata` (tuple): Metadata associated with the field

## FieldSpecIterable

The `FieldSpecIterable` type represents the output of an adapter:

```python
FieldSpecIterable = Iterator[tuple[str, type, tuple]]
```
