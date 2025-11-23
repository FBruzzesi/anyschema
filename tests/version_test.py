from __future__ import annotations

import re
from pathlib import Path

import anyschema


def test_version_matches_pyproject() -> None:
    """Tests version is same of pyproject."""
    with Path("pyproject.toml").open(encoding="utf-8") as file:
        content = file.read()
        pyproject_version = re.search(r'version = "(.*)"', content).group(1)  # type: ignore[union-attr]

    assert anyschema.__version__ == pyproject_version
