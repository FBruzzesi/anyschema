from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typing_extensions import Any, assert_type

import anyschema


def test_version_matches_pyproject() -> None:
    """Tests version is same of pyproject."""
    with Path("pyproject.toml").open(encoding="utf-8") as file:
        content = file.read()
        pyproject_version = re.search(r'version = "(.*)"', content).group(1)  # type: ignore[union-attr]

    assert anyschema.__version__ == pyproject_version


def test_package_getattr() -> None:
    assert_type(anyschema.__version__, str)
    assert_type(anyschema.__title__, str)
    assert_type(anyschema.__all__, tuple[str, ...])

    if TYPE_CHECKING:
        bad = anyschema.not_real  # type: ignore[attr-defined]
        assert_type(bad, Any)

    with pytest.raises(AttributeError):
        very_bad = anyschema.not_real  # type: ignore[attr-defined]  # noqa: F841
