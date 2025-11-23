sources = src tests

lint:
	uvx ruff version
	uvx ruff format $(sources)
	uvx ruff check $(sources) --fix
	uvx ruff clean

test:
	uv run --active --no-sync --group tests pytest tests --cov=src --cov=tests --cov-fail-under=90
	uv run --active --no-sync --group tests pytest src --doctest-modules

typing:
	uv run --active --no-sync --group typing pyright src
	uv run --active --no-sync --group typing mypy src

docs-serve:
	uv run --active --no-sync --group docs mkdocs serve

docs-build:
	uv run --active --no-sync --group docs mkdocs build --strict

docs-deploy:
	uv run --active --no-sync --group docs mkdocs gh-deploy --force
