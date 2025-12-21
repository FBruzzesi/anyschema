# AGENTS.md

This file provides guidance for AI coding agents working on the `anyschema` project.

## Project Overview

`anyschema` converts type specifications (Pydantic models, SQLAlchemy tables, TypedDict, dataclasses, attrs classes,
or plain Python dicts) to dataframe schemas (PyArrow, Polars, Pandas) using Narwhals as an intermediate representation.

## Key architectural principles

1. **Pipeline architecture:** Spec adapters normalize inputs → Parser pipeline converts types to Narwhals dtypes →
    Output format
2. **Dependency isolation:** Core codebase in `anyschema/` must be dependency-free except for:
    - Core dependencies: `narwhals` and `typing_extensions` (can always imported directly)
    - Library-specific files: `anyschema/parsers/{pydantic,attrs,sqlalchemy}.py` (never imported directly;
        loaded conditionally via `_dependencies.py`)
3. **Lazy imports:** Optional dependencies (Pydantic, attrs, SQLAlchemy) are checked via
    `anyschema/_dependencies.py` and only imported when available
4. **Parser order matters**: `ForwardRefStep` → `UnionTypeStep` → `AnnotatedStep` → `AnnotatedTypesStep` →
    `PydanticTypeStep` → `PyTypeStep`

Read `docs/architecture.md` for complete details on the pipeline design.

## Essential Commands

All commands use `uv` in the **active environment** (no virtual environment creation). Always run from repository root.

### Testing

```bash
# Run full test suite with coverage (requires >90% coverage)
uv run --active --no-sync --group tests pytest tests --cov=anyschema --cov=tests --cov-fail-under=90

# Run tests for a specific module
uv run --active --no-sync --group tests pytest tests/parsers/

# Run a specific test file
uv run --active --no-sync --group tests pytest tests/parsers/_builtin_test.py

# Run a specific test function
uv run --active --no-sync --group tests pytest tests/parsers/_builtin_test.py::test_specific_function

# Run doctests in source code
uv run --active --no-sync --group tests pytest anyschema --doctest-modules

# Run tests with verbose output
uv run --active --no-sync --group tests pytest tests -v

# Run tests and stop at first failure
uv run --active --no-sync --group tests pytest tests -x
```

### Linting and Formatting

```bash
# Run all linting and formatting (auto-fixes issues)
make lint

# Or run individual commands:
uvx ruff format anyschema tests
uvx ruff check anyschema tests --fix
uv tool run rumdl check .  # Markdown linting
```

**Important**: Always run `make lint` before committing. The project uses ruff with strict settings.

### Type Checking

```bash
# Run all type checkers
make typing

# Or run individually:
uv run --active --no-sync --group typing pyright anyschema
uv run --active --no-sync --group typing mypy anyschema
```

**Note**: Only type-check the `anyschema/` directory, not `tests/`.

### Documentation

```bash
# Serve docs locally with hot-reload (watches anyschema/ and docs/)
make docs-serve

# Build docs (strict mode - fails on warnings)
make docs-build
```

Documentation uses MkDocs with mkdocstrings for API reference generation.

## Code Style and Conventions

### Python Style

- **Python version**: Minimum 3.10, test on 3.10-3.14
- **Formatting**: Ruff (120 line length, Google docstring convention)
- **Imports**: Every file must start with `from __future__ import annotations`
- **Type hints**: Fully typed codebase (`disallow_untyped_defs = true`)
- **Docstrings**: Google style, comprehensive for all public APIs

### Testing Conventions

**Critical**: Use `pytest` with **function-based tests**, NOT `unittest` classes.

```python
# ✓ GOOD - Function-based pytest
def test_pydantic_adapter_basic():
    """Test that pydantic_adapter correctly extracts fields."""
    # Test implementation
    assert result == expected


# ✗ BAD - unittest classes
class TestPydanticAdapter(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(result, expected)
```

**Testing best practices:**

- Use descriptive test names: `test_<feature>_<scenario>_<expected_outcome>`
- Use fixtures from `tests/conftest.py` (e.g., `auto_pipeline`, `pydantic_student_cls`)
- Parametrize tests for multiple scenarios: `@pytest.mark.parametrize(...)`
- Test both success and error cases
- Coverage requirement: >90% overall, >95% for non-excluded files
- Keep test files alongside corresponding source files (e.g., `tests/parsers/_builtin_test.py` for
    `anyschema/parsers/_builtin.py`)

### Dependency Management

**Core principle**: Keep `anyschema/` dependency-free except for specific patterns.

1. **Always allowed** (import directly):
    - `narwhals` (import as `nw`)
    - `typing_extensions`
    - Standard library

2. **Library-specific files** (can import their library):
    - `anyschema/parsers/pydantic.py` can import `pydantic`
    - `anyschema/parsers/attrs.py` can import `attrs`
    - `anyschema/parsers/sqlalchemy.py` can import `sqlalchemy`

3. **Conditional checks** (use `_dependencies.py`):

    ```python
    # ✓ GOOD - Check before importing
    from anyschema._dependencies import PYDANTIC_AVAILABLE, is_pydantic_base_model

    if PYDANTIC_AVAILABLE:
        from anyschema.parsers.pydantic import PydanticTypeStep

    # ✗ BAD - Direct import in main code
    from pydantic import BaseModel  # Allowed only in parsers/pydantic.py!
    ```

4. **Runtime type checking**:
    - Use `_dependencies.py` functions: `is_pydantic_base_model()`, `is_attrs_class()`, `is_sqlalchemy_table()`
    - These use `sys.modules.get()` to avoid unnecessary imports

### Architecture-Specific Rules

**Parser Steps:**

- Return `None` if your parser can't handle a type (lets next parser try)
- Use `self.pipeline.parse(..., constraints=constraints, metadata=metadata)` for recursion
- Always pass metadata through: `metadata=metadata`
- Order matters: specialized parsers before general ones

**Adapters:**

- Must yield `(name, type, constraints, metadata)` tuples
- `constraints` is a tuple (often empty `()`)
- `metadata` is a dict (often empty `{}`)

**Metadata keys:**

- Use `anyschema/` prefix for custom metadata: `anyschema/time_zone`, `anyschema/time_unit`
- Preserve metadata from input specs (Pydantic Field, attrs field metadata, SQLAlchemy column info)

## Documentation Requirements

**Documentation is critical and must be kept up-to-date with every change.**

### API Documentation

- **Docstrings**: Every public class, function, and method needs comprehensive Google-style docstrings
- **Examples**: Include `Examples:` section in docstrings with realistic usage
- **Type hints**: Always use type hints; docstrings should not duplicate type information
- **Doctests**: Consider adding doctests for simple examples

```python
def parse_type(
    tp: type, constraints: tuple = (), metadata: dict | None = None
) -> nw.DType:
    """Parse a Python type into a Narwhals dtype.

    Args:
        tp: Python type to parse
        constraints: Tuple of constraint objects (e.g., from annotated_types)
        metadata: Additional metadata dict for the field

    Returns:
        Corresponding Narwhals dtype

    Raises:
        NotImplementedError: If no parser can handle the type

    Examples:
        >>> parse_type(int)
        Int64()
        >>> parse_type(str)
        String()
    """
```

### User Documentation

When changing functionality:

1. **Update relevant docs** in `docs/`:
    - `docs/user-guide/getting-started.md` - Basic usage examples
    - `docs/user-guide/advanced.md` - Custom parsers/adapters
    - `docs/user-guide/field-metadata.md` - Metadata handling
    - `docs/architecture.md` - Architecture changes
2. **Update README.md** if user-facing behavior changes
3. **Add/update examples** that demonstrate the feature
4. **Test documentation examples**: Use `markdown-exec` code blocks that actually run

### Documentation Testing

All code examples in documentation are executed during docs build.

In markdown files, use exec="true" to run examples

````md
```python exec="true" source="above" result="python" session="example"
from anyschema import AnySchema

schema = AnySchema(spec={"id": int})
print(schema.to_arrow())
```
````

## Common Workflows

### Adding a New Parser Step

1. **Create parser class** inheriting from `ParserStep` in appropriate file (`anyschema/parsers/`)
2. **Implement `parse()` method** - return `None` if can't handle type
3. **Add to pipeline** in `anyschema/parsers/__init__.py` → `make_pipeline()`
4. **Position correctly** - order matters! Consider dependencies on other parsers
5. **Write tests** in `tests/parsers/` - test success cases, edge cases, and returns `None` when appropriate
6. **Update docs** - add to architecture.md parser table, add examples to user guide
7. **Run full test suite** and type checking

### Adding Support for a New Library

1. **Create parser file**: `anyschema/parsers/newlib.py` (can import `newlib` directly)
2. **Add adapter function**: `anyschema/adapters.py` → `newlib_adapter()`
3. **Add dependency checks**: `anyschema/_dependencies.py` → `NEWLIB_AVAILABLE`, `is_newlib_type()`
4. **Update AnySchema**: `anyschema/_anyschema.py` → add conditional import and adapter registration
5. **Optional dependency**: Add to `pyproject.toml` → `[project.optional-dependencies]`
6. **Tests**: Create `tests/adapters/newlib_adapter_test.py` and `tests/parsers/newlib_test.py`
7. **Documentation**: Add examples to getting-started.md
8. **Run tests**: `uv sync --group tests && make test`

### Fixing a Bug

1. **Write a failing test** that reproduces the bug
2. **Fix the bug** in the source code
3. **Verify test passes** and coverage remains ≥90%
4. **Run linting and type checking**: `make lint && make typing`
5. **Check if docs need updates** - especially if behavior changed
6. **Run full test suite** before committing

### Making a Release

Code agents should **NEVER** make a release. Releases happen automatically via github.

## Troubleshooting

### Tests failing with import errors

- Check `_dependencies.py` is correctly checking for optional libraries
- Library-specific files should only be imported conditionally

### Type checking errors

- Ensure `from __future__ import annotations` is first import
- Check that TYPE_CHECKING blocks are used for type-only imports
- Use `typing_extensions` for newer typing features (backports to 3.10)

### Coverage failures

- Minimum 90% required overall
- Some files exempt (see `pyproject.toml` → `[tool.coverage.report]`)
- Add `# pragma: no cover` for truly untestable code (use sparingly)

### Parser not being called

- Check parser order in `make_pipeline()`
- Ensure earlier parsers return `None` (not raise exceptions)
- Verify parser is added to the pipeline for the correct mode (`"auto"` vs specific)

### Documentation build failures

- Run `make docs-build` to see specific errors
- Check that all code examples in docs are valid
- Ensure mkdocstrings can import all documented modules

## Project-Specific Quirks

1. **Version is dynamic**: `__version__` uses `__getattr__` and reads from package metadata
   (see `anyschema/__init__.py`)
2. **Test fixtures are shared**: Many test fixtures in `tests/conftest.py` - use them!
3. **Parser pipeline is cached**: The `make_pipeline()` result can be reused, but parsers maintain pipeline reference
4. **Narwhals as intermediate**: All conversions go through Narwhals → then to target format
5. **Metadata preservation**: Always pass `metadata=metadata` when recursing in parsers
6. **Column ordering**: Use `OrderedDict` to preserve field order from specs

## Performance Considerations

- Avoid importing optional dependencies unless needed (use lazy imports)
- Parser pipeline stops at first match (order fast paths first)
- Narwhals is lightweight - don't avoid creating intermediate schemas
- Type inspection via `typing.get_type_hints()` can be expensive on large models

## Additional Resources

- [Documentation](https://fbruzzesi.github.io/anyschema/)
- [Repository](https://github.com/fbruzzesi/anyschema)
- Architecture deep-dive: Read `docs/architecture.md` first!

## Before You Start

1. Read `docs/architecture.md` to understand the pipeline design
2. Review existing parsers in `anyschema/parsers/` for patterns
3. Check `tests/conftest.py` for available fixtures
4. Run `make lint && make typing && make test` to ensure working state
5. **Most importantly**: Keep documentation updated with every change!
