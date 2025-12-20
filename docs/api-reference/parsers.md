# Parsers

## Pipeline

A parser pipeline is a sequence of [parser steps](#parser-steps) that process type annotations to produce Narwhals
dtypes.

::: anyschema.parsers.ParserPipeline
    handler: python
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: anyschema.parsers.make_pipeline
    handler: python
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

## Parser Steps

Parser steps are the building blocks of the type parsing pipeline. Each step handles specific type patterns.

For more details on how these work together, see the [parser steps](../architecture.md#parser-steps)
section in the Architecture guide.

::: anyschema.parsers.ParserStep
    handler: python
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

---

The following steps are built-in and come dependency-free.

::: anyschema.parsers.ForwardRefStep
    handler: python
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: anyschema.parsers.UnionTypeStep
    handler: python
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: anyschema.parsers.AnnotatedStep
    handler: python
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: anyschema.parsers.PyTypeStep
    handler: python
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

---

::: anyschema.parsers.annotated_types.AnnotatedTypesStep
    handler: python
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: anyschema.parsers.attrs.AttrsTypeStep
    handler: python
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: anyschema.parsers.pydantic.PydanticTypeStep
    handler: python
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3

::: anyschema.parsers.sqlalchemy.SQLAlchemyTypeStep
    handler: python
    options:
      show_root_heading: true
      show_source: false
      heading_level: 3
