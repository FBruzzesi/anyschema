# OpenAPI Compatibility

`anyschema` supports OpenAPI-compatible metadata through the `x-anyschema` prefix, which is an extension point defined
in the [OpenAPI specification](https://swagger.io/specification/#specification-extensions).

## What is OpenAPI?

OpenAPI (formerly known as Swagger) is a widely-adopted specification for describing REST APIs.
It allows you to define your API's structure, endpoints, request/response formats, and more in a standardized way.

## Extension fields in OpenAPI

The OpenAPI specification allows custom extensions through fields prefixed with `x-`.
These extension fields can contain any valid JSON and are used to add vendor-specific or custom information that's not
part of the core OpenAPI specification.

## Using `x-anyschema` prefix

In `anyschema`, you can use either `"anyschema"` or `"x-anyschema"` as the metadata namespace key.
Both work identically:

```python exec="true" source="above" result="python" session="openapi-intro"
from pydantic import BaseModel, Field
from anyschema import AnySchema


class Product(BaseModel):
    # Standard anyschema format
    name: str = Field(json_schema_extra={"anyschema": {"nullable": False}})

    # OpenAPI-compatible format (with x- prefix)
    price: float = Field(json_schema_extra={"x-anyschema": {"nullable": True}})


schema = AnySchema(spec=Product)

print(f"name nullable: {schema.fields['name'].nullable}")
print(f"price nullable: {schema.fields['price'].nullable}")
```

## Why support `x-anyschema`?

There are several reasons to support the `x-anyschema` prefix:

1. **OpenAPI Integration**: If you're generating OpenAPI specifications from Pydantic models and want to include
    anyschema metadata, using the `x-` prefix makes it clear that this is an extension field.

2. **Tool Compatibility**: Some OpenAPI tools and validators may flag unknown fields without the `x-` prefix as errors.
    Using `x-anyschema` ensures better compatibility.

3. **Standards Compliance**: Following the OpenAPI convention makes your API documentation more standardized and easier
    for other developers to understand.

## Choosing between `anyschema` and `x-anyschema`

Both formats work identically in `anyschema`. Choose based on your needs:

* Use `"anyschema"` if:
    * You're only using anyschema internally
    * You want cleaner, shorter metadata keys
    * You're not generating OpenAPI specifications

* Use `"x-anyschema"` if:
    * You're generating OpenAPI specifications
    * You want to be explicit that this is an extension field
    * You're integrating with OpenAPI tooling
    * You want maximum standards compliance

## Mixing both formats

!!! warning
    You should **not** mix both formats in the same metadata dictionary.

    If both `"anyschema"` and `"x-anyschema"` are present, `anyschema` will use whichever it finds first
    (with `"anyschema"` taking precedence).

```python
# ❌ Don't do this - mixing both formats
metadata = {
    "anyschema": {"nullable": True},
    "x-anyschema": {"unique": True},  # This will be ignored!
}

# ✅ Do this - use one format consistently
metadata = {
    "x-anyschema": {
        "nullable": True,
        "unique": True,
    }
}
```

## Further Reading

* [OpenAPI Specification](https://swagger.io/specification/)
* [OpenAPI Extension Fields](https://swagger.io/specification/#specification-extensions)
* [Pydantic and OpenAPI](https://docs.pydantic.dev/latest/concepts/json_schema/)
