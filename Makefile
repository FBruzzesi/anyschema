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
