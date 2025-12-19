from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from anyschema import show_versions

if TYPE_CHECKING:
    import pytest


def test_show_versions(capsys: pytest.CaptureFixture[str]) -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        show_versions()
        out, _ = capsys.readouterr()

    assert "python" in out
    assert "machine" in out

    assert "anyschema" in out
    assert "narwhals" in out
    assert "typing_extensions" in out
    assert "attrs" in out
    assert "pydantic" in out
    assert "sqlalchemy" in out
    assert "pandas" in out
    assert "polars" in out
    assert "pyarrow" in out

    assert "numpy" not in out
