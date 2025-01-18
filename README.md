# anyschema: From pydantic to any frame schema

This is a simple example of how to convert a pydantic model to a frame schema.

```python
from anyschema import AnySchema
from pydantic import BaseModel
from pydantic import PositiveInt


class Student(BaseModel):
    name: str
    age: PositiveInt
    classes: list[str]


anyschema = AnySchema(model=Student)

# Convert to pyarrow schema
pa_schema = anyschema.to_arrow()

type(pa_schema)
# pyarrow.lib.Schema

pa_schema
# name: string
# age: uint64
# classes: list<item: string>
#   child 0, item: string

pl_schema = anyschema.to_polars()

type(pl_schema)
# polars.schema.Schema

pl_schema
# Schema([('name', String), ('age', UInt64), ('classes', List(String))])
```

## Why does this exist?

Mostly... just because of curiosity to see if it could be done generically through Narwhals.

I recently caught up with a Talk Python podcast episode in which the creator of LanceDB was interviewed.
He mentioned that they need to convert from pydantic models to pyarrow schemas ([Reference](https://www.youtube.com/live/wuGirNCyTxA?t=2880s)).

This could (easily?) be generalized to many other dataframe schema by translating to Narwhals first.
