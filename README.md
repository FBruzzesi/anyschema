# anyschema: From Type Specifications to Dataframe Schemas

> [!CAUTION]
> `anyschema` is still in early development and possibly unstable.

---

[Documentation](https://fbruzzesi.github.io/anyschema/) | [Source Code](https://github.com/fbruzzesi/anyschema/) | [Issue Tracker](https://github.com/fbruzzesi/anyschema/issues)

---

`anyschema` allows you to convert from type specifications (such as Pydantic models, SQLAlchemy tables, TypedDict,
dataclasses, or plain Python dicts) to _any_ dataframe schema (by _"any"_ we intend those supported by Narwhals).

Let's see how it works in practice with an example:

```python
from anyschema import AnySchema
from pydantic import BaseModel
from pydantic import PositiveInt


class Student(BaseModel):
    name: str
    age: PositiveInt
    classes: list[str]


schema = AnySchema(spec=Student)

# Convert to pyarrow schema
pa_schema = schema.to_arrow()

type(pa_schema)
# pyarrow.lib.Schema

pa_schema
# name: string
# age: uint64
# classes: list<item: string>
#   child 0, item: string

pl_schema = schema.to_polars()

type(pl_schema)
# polars.schema.Schema

pl_schema
# Schema([('name', String), ('age', UInt64), ('classes', List(String))])
```

To read more about `anyschema` functionalities and features consider checking out the
[documentation](https://fbruzzesi.github.io/anyschema/) website.

## Installation

`anyschema` is available on [pypi](https://pypi.org/project/anyschema/), and it can be installed directly via
any package manager. For instance:

```bash
uv pip install "anyschema[pydantic]"
# or with SQLAlchemy support
uv pip install "anyschema[sqlalchemy]"
```

To allow interoperability with Pydantic models or SQLAlchemy tables.

## When to use `anyschema`

`anyschema` is designed for scenarios where type specifications (e.g., Pydantic models, SQLAlchemy tables) serve as a
single source of truth for both validation and dataframe schema generation.

The typical use cases are: Data pipelines, database-to-dataframe workflows, API to database workflows, schema
generation, type-safe data processing.

## Why `anyschema`?

The project was inspired by a [Talk Python podcast episode](https://www.youtube.com/live/wuGirNCyTxA?t=2880s) featuring
the creator of [LanceDB](https://github.com/lancedb/lancedb), who mentioned the need to convert from Pydantic models to
PyArrow schemas.

This challenge led to a realization: such conversion could be generalized to many dataframe libraries by using Narwhals
as an intermediate representation. `anyschema` makes this conversion seamless and extensible.
