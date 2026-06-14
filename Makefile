ARG := $(word 2, $(MAKECMDGOALS))
$(eval $(ARG):;@:)

sources = src tests

lint:
	uvx ruff version
	uvx ruff format $(sources)
	uvx ruff check $(sources) --fix
	uvx ruff clean
	uv tool run rumdl check .

test:
	uv run --group testing pytest tests --cov=src --cov=tests
	uv run --group testing pytest src --doctest-modules

typing:
	uv run --group typing pyright $(sources)
	uv run --group typing mypy $(sources)

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
