# Architecture

This document explains how anyschema works under the hood and describes its modular design based on **Type Parsers** and **Spec Adapters**.

## Overview

anyschema uses a composable parser chain architecture to convert type specifications into dataframe schemas. The design provides:

- **Modularity**: Each parser handles a specific type concern
- **Composability**: Parsers can be combined in different orders
- **Extensibility**: New parsers can be added without modifying existing code
- **Recursion simplification**: Union/Optional types are unwrapped once, ForwardRefs resolved first
- **Metadata preservation**: Constraints flow through the parsing chain correctly

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         AnySchema                           │
│                     (Main Entry Point)                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
          ┌───────────────────────────────┐
          │      Spec Adapter             │
          │  (pydantic_adapter or         │
          │   into_ordered_dict_adapter)  │
          └───────────────┬───────────────┘
                          │
                          │ Yields (name, type, metadata)
                          ▼
          ┌───────────────────────────────┐
          │       Parser Chain            │
          │   (Tries parsers in order)    │
          └───────────────┬───────────────┘
                          │
                          │ Delegates to parsers in order:
                          │
      ┌───────────────────┼───────────────────┐
      │                   │                   │
      ▼                   ▼                   ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Forward    │   │   Union     │   │  Annotated  │
│    Ref      │   │   Type      │   │   Parser    │
│   Parser    │   │   Parser    │   │             │
└─────────────┘   └─────────────┘   └─────────────┘
      │                   │                   │
      └───────────────────┼───────────────────┘
                          │
      ┌───────────────────┼───────────────────┐
      │                   │                   │
      ▼                   ▼                   ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ Annotated   │   │  Pydantic   │   │   Python    │
│   Types     │   │    Type     │   │    Type     │
│   Parser    │   │   Parser    │   │   Parser    │
└─────────────┘   └─────────────┘   └─────────────┘
      │                   │                   │
      └───────────────────┴───────────────────┘
                          │
                          ▼
                  Narwhals DType
                          │
                          ▼
          ┌───────────────────────────────┐
          │       Narwhals Schema         │
          └───────────────┬───────────────┘
                          │
      ┌───────────────────┼───────────────────┐
      │                   │                   │
      ▼                   ▼                   ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  PyArrow    │   │   Polars    │   │   Pandas    │
│   Schema    │   │   Schema    │   │   Schema    │
└─────────────┘   └─────────────┘   └─────────────┘
```

## Core Components

### 1. Spec Adapters

**Spec Adapters** convert input specifications into a standardized format that the parser chain can process. They yield tuples of `(field_name, field_type, metadata)` for each field.

#### Built-in Adapters

##### `pydantic_adapter`

Extracts field information from Pydantic models:

```python
from pydantic import BaseModel, Field
from anyschema.adapters import pydantic_adapter


class Student(BaseModel):
    name: str
    age: int = Field(ge=0)


for field_name, field_type, metadata in pydantic_adapter(Student):
    print(f"{field_name}: {field_type}, metadata={metadata}")
# name: <class 'str'>, metadata=()
# age: <class 'int'>, metadata=(Ge(ge=0),)
```

Key features:
- Extracts field annotations
- Preserves Pydantic field metadata
- Works with both `Field()` constraints and `Annotated` types

##### `into_ordered_dict_adapter`

Converts Python mappings or sequences to field specifications:

```python
from anyschema.adapters import into_ordered_dict_adapter

# From dictionary
spec = {"name": str, "age": int}
for field_name, field_type, metadata in into_ordered_dict_adapter(spec):
    print(f"{field_name}: {field_type}")

# From list of tuples
spec = [("name", str), ("age", int)]
for field_name, field_type, metadata in into_ordered_dict_adapter(spec):
    print(f"{field_name}: {field_type}")
```

Key features:
- Accepts `dict` or `list[tuple[str, type]]`
- Preserves order (using OrderedDict internally)
- No metadata (always returns empty tuple)

### 2. Type Parsers

**Type Parsers** are responsible for converting type annotations into Narwhals dtypes. Each parser handles specific type patterns.

#### TypeParser ABC

All parsers inherit from the `TypeParser` abstract base class:

```python
from abc import ABC, abstractmethod
from narwhals.dtypes import DType


class TypeParser(ABC):
    """Abstract base class for type parsers."""

    _parser_chain: ParserChain | None = None

    @property
    def parser_chain(self) -> ParserChain:
        """Access the parser chain for recursive parsing."""
        ...

    @abstractmethod
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        """Parse a type annotation into a Narwhals dtype.

        Returns:
            A Narwhals DType if this parser can handle the type, None otherwise.
        """
        ...
```

Key concepts:
- Returns `DType` if the parser can handle the type
- Returns `None` if it cannot (allows next parser to try)
- Has access to `parser_chain` for recursive parsing of nested types
- Receives `metadata` tuple with constraints/annotations

#### Built-in Parsers

##### 1. ForwardRefParser

**Purpose**: Resolve `ForwardRef` to actual types

**Handles**: `ForwardRef('int')`, `ForwardRef('Optional[int]')`, etc.

**Order**: **First** (must resolve before other parsers can work)

```python
from typing import ForwardRef
from anyschema.parsers import ForwardRefParser

parser = ForwardRefParser()
result = parser.parse(ForwardRef("int"))
# Result: Int64
```

**Why first?**: `ForwardRef('Optional[int]')` must become `Optional[int]` before `UnionTypeParser` can extract `int`.

##### 2. UnionTypeParser

**Purpose**: Extract non-None type from Union/Optional types

**Handles**: `Union[T, None]`, `T | None`, `Optional[T]`

**Order**: Second (unwraps optionals before other parsers see them)

```python
from anyschema.parsers import UnionTypeParser

parser = UnionTypeParser()
result = parser.parse(int | None)
# Recursively parses `int`, returns its dtype
```

**Metadata preservation**: When unwrapping `Annotated[Optional[int], Gt(0)]`, the `Gt(0)` metadata is preserved and passed to the next parser.

##### 3. AnnotatedParser

**Purpose**: Extract base type and metadata from `typing.Annotated`

**Handles**: `Annotated[T, metadata...]`

**Order**: Third (unwraps annotations before type checking)

```python
from typing import Annotated
from annotated_types import Gt
from anyschema.parsers import AnnotatedParser

parser = AnnotatedParser()
result = parser.parse(Annotated[int, Gt(0)])
# Extracts `int` and metadata `(Gt(0),)`, then recursively parses
```

##### 4. AnnotatedTypesParser

**Purpose**: Refine types based on `annotated_types` metadata

**Handles**: Integer constraints (Gt, Ge, Lt, Le, Interval)

**Order**: Fourth (refines types after unwrapping)

**Intelligence**:
- Determines smallest integer dtype that fits constraints
- Chooses unsigned (UInt) vs signed (Int) based on lower bound

```python
from typing import Annotated
from annotated_types import Gt, Interval
from anyschema.parsers import AnnotatedTypesParser

parser = AnnotatedTypesParser()

# Positive values → UInt64
result = parser.parse(int, metadata=(Gt(0),))

# Fits in 8 bits unsigned → UInt8
result = parser.parse(int, metadata=(Interval(ge=0, le=255),))

# Fits in 8 bits signed → Int8
result = parser.parse(int, metadata=(Interval(ge=-128, le=127),))
```

##### 5. PydanticTypeParser

**Purpose**: Handle Pydantic-specific types

**Handles**:
- Datetime types: `NaiveDatetime`, `PastDatetime`, `FutureDatetime`
- Date types: `PastDate`, `FutureDate`
- `BaseModel`: Converted to `Struct` with recursive field parsing

**Order**: Fifth (before fallback to Python types)

```python
from pydantic import BaseModel, PositiveInt
from anyschema.parsers import PydanticTypeParser


class Address(BaseModel):
    street: str
    city: str


parser = PydanticTypeParser()
result = parser.parse(Address)
# Result: Struct with fields [Field("street", String), Field("city", String)]
```

**Raises error for**: `AwareDatetime` (no fixed timezone)

##### 6. PyTypeParser

**Purpose**: Handle standard Python types (fallback)

**Handles**:
- Primitives: `int`, `str`, `float`, `bool`
- Temporal: `datetime`, `date`, `time`, `timedelta`
- Containers: `list[T]`, `tuple[T, ...]`, `Sequence[T]`, `Iterable[T]`
- Other: `Decimal`, `bytes`, `Enum`

**Order**: Last (fallback for basic types)

```python
from anyschema.parsers import PyTypeParser

parser = PyTypeParser()

# Basic types
result = parser.parse(int)  # → Int64
result = parser.parse(str)  # → String
result = parser.parse(bool)  # → Boolean

# Container types (recursive)
result = parser.parse(list[int])  # → List(Int64)
result = parser.parse(list[list[str]])  # → List(List(String))
```

### 3. ParserChain

The `ParserChain` orchestrates multiple parsers and tries each one in sequence:

```python
from anyschema.parsers import ParserChain, PyTypeParser, PydanticTypeParser

chain = ParserChain([parser1, parser2, parser3])

# Strict mode (default) - raises if no parser succeeds
dtype = chain.parse(some_type, strict=True)

# Non-strict mode - returns None if no parser succeeds
dtype = chain.parse(some_type, strict=False)
```

**Key features**:
- Tries each parser in order until one returns a non-None result
- Automatically wires itself to each parser's `parser_chain` property
- Supports both strict and non-strict modes

## Parser Order

The order of parsers is crucial for correct behavior:

```
1. ForwardRefParser      → Resolve ForwardRef('T') to T
2. UnionTypeParser       → Unwrap Optional[T] to T (preserving metadata)
3. AnnotatedParser       → Extract Annotated[T, ...] to T with metadata
4. AnnotatedTypesParser  → Refine T based on metadata (e.g., int + Gt(0) → UInt64)
5. PydanticTypeParser    → Handle Pydantic-specific types
6. PyTypeParser          → Handle basic Python types (fallback)
```

### Why This Order?

**Example: `Annotated[Optional[int], Gt(0)]`**

1. **AnnotatedParser**: Extracts `Optional[int]` with metadata `(Gt(0),)`
2. **UnionTypeParser**: Extracts `int` and **preserves** metadata `(Gt(0),)`
3. **AnnotatedTypesParser**: Receives `int` with metadata `(Gt(0),)` and refines to `UInt64`

✅ **Result**: `UInt64` (constraint properly applied)

Without this order, the constraint would be lost and we'd get `Int64` instead.

## Metadata Preservation

A key feature of the architecture is proper metadata preservation through the parsing chain.

### Example Flow

For `Annotated[int | None, Gt(0)]`:

```
Input: Annotated[int | None, Gt(0)]
                    │
                    ▼
       ┌─────────────────────────┐
       │   AnnotatedParser       │  Extracts: int | None
       │   metadata=(Gt(0),)     │  Passes metadata down
       └───────────┬─────────────┘
                   │
                   ▼
       ┌─────────────────────────┐
       │   UnionTypeParser       │  Extracts: int
       │   Preserves: (Gt(0),)   │  Keeps metadata!
       └───────────┬─────────────┘
                   │
                   ▼
       ┌─────────────────────────┐
       │  AnnotatedTypesParser   │  Receives: int, (Gt(0),)
       │  Refines: UInt64        │  Applies constraint
       └───────────┬─────────────┘
                   │
                   ▼
              Result: UInt64
```

Without metadata preservation, `Gt(0)` would be lost during Union unwrapping!

## Recursion

Parsers can recursively call the chain for nested types via the `parser_chain` property:

```python
class PyTypeParser(TypeParser):
    def parse(self, input_type, metadata=()):
        if is_list_type(input_type):
            inner_type = get_inner_type(input_type)
            # Recursively parse inner type using the full chain
            inner_dtype = self.parser_chain.parse(inner_type, strict=True)
            return nw.List(inner=inner_dtype)
        ...
```

This allows parsing of complex nested structures:
- Nested lists: `list[list[int]]`
- Optional nested types: `list[int | None]`
- Complex structures: `list[BaseModel]`
- Forward refs in nested types: `list[ForwardRef('int')]`

## Complete Flow Example

Let's trace a complete example through the system:

```python
from pydantic import BaseModel, PositiveInt
from anyschema import AnySchema


class Student(BaseModel):
    name: str
    age: PositiveInt
    classes: list[str]


schema = AnySchema(spec=Student)
```

### Step-by-Step Flow

1. **AnySchema.__init__**
   - Detects `Student` is a Pydantic model
   - Calls `pydantic_adapter(Student)`

2. **pydantic_adapter**
   - Yields: `("name", str, ())`
   - Yields: `("age", PositiveInt, ())`
   - Yields: `("classes", list[str], ())`

3. **Parser Chain processes "name: str"**
   - ForwardRefParser: Not a ForwardRef → returns None
   - UnionTypeParser: Not a Union → returns None
   - AnnotatedParser: Not Annotated → returns None
   - AnnotatedTypesParser: No metadata → returns None
   - PydanticTypeParser: Not Pydantic type → returns None
   - PyTypeParser: Matches `str` → **returns String()**

4. **Parser Chain processes "age: PositiveInt"**
   - ForwardRefParser: Not a ForwardRef → returns None
   - UnionTypeParser: Not a Union → returns None
   - AnnotatedParser: Extracts `int` with metadata `(Gt(0),)` → recurses
     - PyTypeParser would return Int64, but...
   - AnnotatedTypesParser: Sees `int` + `Gt(0)` → **returns UInt64()**

5. **Parser Chain processes "classes: list[str]"**
   - ForwardRefParser: Not a ForwardRef → returns None
   - UnionTypeParser: Not a Union → returns None
   - AnnotatedParser: Not Annotated → returns None
   - AnnotatedTypesParser: No metadata → returns None
   - PydanticTypeParser: Not Pydantic type → returns None
   - PyTypeParser: Matches `list[T]` → recurses on `str`
     - Inner: `str` → String()
   - **Returns List(String())**

6. **Narwhals Schema Creation**
   ```python
   Schema({"name": String(), "age": UInt64(), "classes": List(String())})
   ```

7. **to_arrow() / to_polars() / to_pandas()**
   - Delegates to Narwhals for backend conversion

## Creating Custom Components

### Custom Parser

To create a custom parser, inherit from `TypeParser`:

```python
from anyschema.parsers import TypeParser
import narwhals as nw


class MyCustomParser(TypeParser):
    def parse(self, input_type: type, metadata: tuple = ()) -> nw.DType | None:
        if input_type is MyCustomType:
            return nw.String()

        # For nested types, use the parser chain
        if is_container_of_my_type(input_type):
            inner = extract_inner_type(input_type)
            inner_dtype = self.parser_chain.parse(inner, strict=True)
            return nw.List(inner_dtype)

        return None  # This parser doesn't handle this type
```

### Custom Adapter

To create a custom adapter, create a function that yields field specifications:

```python
from typing import Generator


def my_custom_adapter(
    spec: MySpecType,
) -> Generator[tuple[str, type, tuple], None, None]:
    """Convert MySpecType to field specifications."""
    for field in spec.get_fields():
        field_name = field.name
        field_type = field.type
        field_metadata = tuple(field.constraints)
        yield field_name, field_type, field_metadata
```

Then use it:

```python
from anyschema import AnySchema

schema = AnySchema(spec=my_spec, adapter=my_custom_adapter)
```

## Benefits of This Architecture

### 1. Modularity
Each parser has a single responsibility:
- Easy to understand and maintain
- Clear separation of concerns
- Testable in isolation
- Each parser is ~50-100 lines of focused code

### 2. Composability
Parsers can be mixed and matched:
- Use only the parsers you need
- Add custom parsers to the chain
- Reorder parsers for different behavior

### 3. Extensibility
Support new type systems without modifying existing code:
- Inherit from `TypeParser` ABC
- Implement the `parse` method
- Add to a parser chain

### 4. Recursion Simplified
Complex type unwrapping is centralized:
- `ForwardRef` resolution in one place
- `Optional[T]` unwrapping in one place
- Subsequent parsers only see unwrapped types

### 5. Metadata Preservation
Constraints flow correctly through the chain:
- `Annotated[Optional[int], Gt(0)]` correctly becomes `UInt64`
- Metadata is preserved through Optional unwrapping
- Type refinement works regardless of Optional nesting

## Performance Considerations

1. **Parser Chain Caching**: The `create_parser_chain` function uses `@lru_cache` to avoid recreating chains
2. **Immutable Parsers**: Parser instances are reused across calls
3. **Early Return**: Parsers return `None` quickly if they don't handle a type
4. **Lazy Evaluation**: ForwardRef resolution only happens when needed

## Next Steps

- See [Advanced Usage](advanced.md) for creating custom parsers and adapters
- Browse the [API Reference](api-reference.md) for detailed documentation
