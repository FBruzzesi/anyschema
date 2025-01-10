# anyschema: From pydantic to any frame schema

This is a simple example of how to convert a pydantic model to a frame schema.

```python
from pydantic import BaseModel
from anyschema import AnySchema

class MyModel(BaseModel):
    id: int
    name: str

schema = AnySchema.from_pydantic(MyModel)
schema.to_arrow()
```

The output will be:

```python
{
    "id": pa.Int64(),
    "name": pa.string()
}
```
