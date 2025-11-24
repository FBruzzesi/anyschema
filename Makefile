sources = anyschema tests

lint:
	uvx ruff version
	uvx ruff format $(sources)
	uvx ruff check $(sources) --fix
	uvx ruff clean

test:
	uv run --active --no-sync --group tests pytest tests --cov=anyschema --cov=tests --cov-fail-under=90
	uv run --active --no-sync --group tests pytest anyschema --doctest-modules

typing:
	uv run --active --no-sync --group typing pyright anyschema
	uv run --active --no-sync --group typing mypy anyschema

docs-serve:
	uv run --active --no-sync --group docs mkdocs serve --watch anyschema --watch docs --dirty

docs-build:
	uv run --active --no-sync --group docs mkdocs build --strict
