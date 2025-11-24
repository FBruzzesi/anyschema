# anyschema: From Type Specifications to Dataframe Schemas

> [!CAUTION]
> `anyschema` is still in early development and not in pypi yet.
> If you are keen to try it out, it is possible to install it via pip anyway:
> `python -m pip install git+https://github.com/FBruzzesi/anyschema.git`

`anyschema` allows you to convert from a pydantic model to _any_ dataframe schema (by _"any"_ we intend those supported
by Narwhals).

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

## Why `anyschema`?

The project was inspired by a [Talk Python podcast episode](https://www.youtube.com/live/wuGirNCyTxA?t=2880s) featuring
the creator of [LanceDB](https://github.com/lancedb/lancedb), who mentioned the need to convert from Pydantic models to
PyArrow schemas.

This challenge led to a realization: such conversion could be generalized to many dataframe libraries by using Narwhals
as an intermediate representation. `anyschema` makes this conversion seamless and extensible.
