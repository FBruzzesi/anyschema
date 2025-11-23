# Parsers

## Making a pipeline

::: anyschema.parsers.make_pipeline
    handler: python
    show_source: true

## Parser Steps

Parser steps are the building blocks of the type parsing pipeline. Each step handles specific type patterns.
For more details on how these work together, see the [Parser Pipeline](architecture.md#parser-pipeline) section in the
Architecture guide.

### ParserStep (Base Class)

::: anyschema.parsers.ParserStep
    handler: python
    show_root_full_path: true
    show_root_heading: true
    show_source: true
    heading_level: 4

### Built-in Parser Steps

::: anyschema.parsers.ForwardRefStep
    handler: python
    show_root_full_path: true
    show_root_heading: true
    show_source: true
    heading_level: 4

::: anyschema.parsers.UnionTypeStep
    handler: python
    show_root_full_path: true
    show_root_heading: true
    show_source: true
    heading_level: 4

::: anyschema.parsers.AnnotatedStep
    handler: python
    show_root_full_path: true
    show_root_heading: true
    show_source: true
    heading_level: 4

::: anyschema.parsers.PyTypeStep
    handler: python
    show_root_full_path: true
    show_root_heading: true
    show_source: true
    heading_level: 4

::: anyschema.parsers.annotated_types.AnnotatedTypesStep
    handler: python
    show_root_full_path: true
    show_root_heading: true
    show_source: true
    heading_level: 4

::: anyschema.parsers.pydantic.PydanticTypeStep
    handler: python
    show_root_full_path: true
    show_root_heading: true
    show_source: true
    heading_level: 4

## ParserPipeline

A parser pipeline is a sequence of parser steps that process type annotations to produce Narwhals dtypes.

::: anyschema.parsers.ParserPipeline
