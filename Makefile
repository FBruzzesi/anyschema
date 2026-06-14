ARG := $(word 2, $(MAKECMDGOALS))
$(eval $(ARG):;@:)

sources = src tests

py-lint:
	uvx ruff version
	uvx ruff format $(sources)
	uvx ruff check $(sources) --fix
	uvx ruff clean

md-lint:
	uvx rumdl version
	uvx rumdl config --no-defaults
	uvx rumdl check --output-format=github .

lint: py-lint md-lint

test:
	uv run --group testing --all-extras pytest tests --cov=src --cov=tests
	uv run --group testing --all-extras pytest src --doctest-modules

typing:
	uv run --group typing --all-extras pyrefly check $(sources) --min-severity info --summary
	uv run --group typing --all-extras pyright $(sources)
	uv run --group typing --all-extras mypy $(sources)

docs-serve:
	uv run --group docs mkdocs serve --watch src --watch docs --dirty

docs-build:
	uv run --group docs mkdocs build --strict

setup-release:
	git checkout main
	git fetch upstream
	git reset --hard upstream/main
	git checkout -b bump-version
	python bump-version.py $(ARG)
	gh pr create --title "release: Bump version to " --body "Bump version" --base main --label release
