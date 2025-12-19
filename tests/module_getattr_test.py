from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typing_extensions import Any, assert_type

import anyschema


def test_package_getattr() -> None:
    assert_type(anyschema.__version__, str)
    assert_type(anyschema.__title__, str)

    if TYPE_CHECKING:
        bad = anyschema.not_real  # type: ignore[attr-defined]
        assert_type(bad, Any)

    with pytest.raises(AttributeError):
        very_bad = anyschema.not_real  # type: ignore[attr-defined]  # noqa: F841
