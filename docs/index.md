# anyschema: From pydantic to any frame schema

`anyschema` allows you to convert from a pydantic model to _any_ dataframe schema[^1].

[^1]: By _"any"_ dataframe, we intend those supported by Narwhals.

Let's see how it works in practice with an example:

```python
from anyschema import AnySchema
from pydantic import BaseModel
from pydantic import PositiveInt


class Student(BaseModel):
    name: str
    age: PositiveInt
    classes: list[str]


schema = AnySchema(model=Student)
```

=== "to arrow"

    ```python
    pa_schema = schema.to_arrow()

    type(pa_schema)
    # pyarrow.lib.Schema

    pa_schema
    # name: string
    # age: uint64
    # classes: list<item: string>
    #   child 0, item: string
    ```

=== "to polars"

    ```python
    pl_schema = schema.to_polars()

    type(pl_schema)
    # polars.schema.Schema

    pl_schema
    # Schema([('name', String), ('age', UInt64), ('classes', List(String))])
    ```

## Why does this exist?

Mostly... just because of curiosity to see if it could be done generically through Narwhals.

I recently caught up with a [Talk Python podcast episode](https://www.youtube.com/live/wuGirNCyTxA?t=2880s) in which the creator of LanceDB was interviewed.
He mentioned that they need to convert from pydantic models to pyarrow schemas.

I thought that this could (easily?) be generalized to many other dataframe schema by translating to Narwhals first.

## API Reference

We are exposing a single class, `AnySchema`, which is the main entry point for all the functionalities we provide.

::: src.anyschema._anyschema.AnySchema
    options:
        show_root_full_path: false
        show_root_heading: true

