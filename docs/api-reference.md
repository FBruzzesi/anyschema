# API Reference

This page provides detailed API documentation for all public classes and functions in anyschema.

## Core Classes

### AnySchema

::: anyschema.AnySchema
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3
        members_order: source
        show_signature_annotations: true

## Type Parsers

Type parsers convert Python type annotations into Narwhals dtypes. All parsers inherit from the `TypeParser` base class.

### TypeParser (Base Class)

::: anyschema.parsers.TypeParser
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3
        members_order: source
        show_signature_annotations: true

### ParserChain

::: anyschema.parsers.ParserChain
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3
        members_order: source
        show_signature_annotations: true

### Built-in Parsers

#### PyTypeParser

::: anyschema.parsers.PyTypeParser
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 4
        members_order: source
        show_signature_annotations: true

#### PydanticTypeParser

::: anyschema.parsers.pydantic.PydanticTypeParser
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 4
        members_order: source
        show_signature_annotations: true

#### AnnotatedParser

::: anyschema.parsers.AnnotatedParser
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 4
        members_order: source
        show_signature_annotations: true

#### UnionTypeParser

::: anyschema.parsers.UnionTypeParser
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 4
        members_order: source
        show_signature_annotations: true

#### ForwardRefParser

::: anyschema.parsers._forward_ref.ForwardRefParser
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 4
        members_order: source
        show_signature_annotations: true

#### AnnotatedTypesParser

::: anyschema.parsers.annotated_types.AnnotatedTypesParser
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 4
        members_order: source
        show_signature_annotations: true

### Parser Factory

#### create_parser_chain

::: anyschema.parsers.create_parser_chain
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3
        show_signature_annotations: true

## Spec Adapters

Spec adapters convert input specifications (Pydantic models, dictionaries, etc.) into a standardized format that the parser chain can process.

### pydantic_adapter

::: anyschema.adapters.pydantic_adapter
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3
        show_signature_annotations: true

### into_ordered_dict_adapter

::: anyschema.adapters.into_ordered_dict_adapter
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3
        show_signature_annotations: true

## Exceptions

### UnavailableParseChainError

::: anyschema.exceptions.UnavailableParseChainError
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

### UnsupportedDTypeError

::: anyschema.exceptions.UnsupportedDTypeError
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

## Type Aliases

anyschema defines several type aliases for better type hints:

### Spec Types

- **`Spec`**: `Schema | IntoOrderedDict | type[BaseModel]` - Valid input specifications
- **`IntoOrderedDict`**: `Mapping[str, type] | Sequence[tuple[str, type]]` - Python mapping-based specs
- **`SpecType`**: `Literal["pydantic", "python"] | None` - Type of spec being parsed

### Parser Types

- **`IntoParserChain`**: `Literal["auto"] | Sequence[TypeParser]` - Parser chain configuration

### Field Types

- **`FieldName`**: `str` - Name of a field
- **`FieldType`**: `type` - Type annotation of a field
- **`FieldMetadata`**: `tuple` - Metadata tuple associated with a field
- **`FieldSpec`**: `tuple[FieldName, FieldType, FieldMetadata]` - Complete field specification

### Adapter Types

- **`FieldSpecIterable`**: `Generator[FieldSpec, None, None]` - Iterator of field specifications
- **`Adapter`**: `Callable[[Any], FieldSpecIterable]` - Adapter function signature

## Usage Examples

### Basic Usage

```python
from anyschema import AnySchema
from pydantic import BaseModel, PositiveInt


class Student(BaseModel):
    name: str
    age: PositiveInt
    classes: list[str]


schema = AnySchema(spec=Student)

# Convert to different formats
pa_schema = schema.to_arrow()
pl_schema = schema.to_polars()
pd_schema = schema.to_pandas()
```

### Custom Parser

```python
from anyschema.parsers import TypeParser, create_parser_chain
import narwhals as nw


class MyCustomParser(TypeParser):
    def parse(self, input_type, metadata=()):
        if input_type is MyCustomType:
            return nw.String()
        return None


parsers = create_parser_chain([MyCustomParser(), ...])
schema = AnySchema(spec=my_spec, parsers=parsers)
```

### Custom Adapter

```python
from anyschema import AnySchema


def my_adapter(spec):
    for field_name, field_type in spec.items():
        yield field_name, field_type, ()


schema = AnySchema(spec=my_spec, adapter=my_adapter)
```

## See Also

- [Getting Started](getting-started.md) - Learn the basics
- [Architecture](architecture.md) - Understand the design
- [Advanced Usage](advanced.md) - Custom parsers and adapters
