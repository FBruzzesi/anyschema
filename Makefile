ARG := $(word 2, $(MAKECMDGOALS))
$(eval $(ARG):;@:)

sources = anyschema tests

lint:
	uvx ruff version
	uvx ruff format $(sources)
	uvx ruff check $(sources) --fix
	uvx ruff clean
	uv tool run rumdl check .

test:
	uv run --active --no-sync --group tests pytest tests --cov=anyschema --cov=tests --cov-fail-under=90
	uv run --active --no-sync --group tests pytest anyschema --doctest-modules

typing:
	uv run --active --no-sync --group typing ty check $(sources) --output-format concise
	uv run --active --no-sync --group typing pyright $(sources)
	uv run --active --no-sync --group typing mypy $(sources)

docs-serve:
	uv run --active --no-sync --group docs mkdocs serve --watch anyschema --watch docs --dirty

docs-build:
	uv run --active --no-sync --group docs mkdocs build --strict

setup-release:
	git checkout main
	git fetch upstream
	git reset --hard upstream/main
	git checkout -b bump-version
	python bump-version.py $(ARG)
	gh pr create --title "release: Bump version to " --body "Bump version" --base main --label release
