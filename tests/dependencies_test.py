from __future__ import annotations

import sys
from unittest.mock import patch

import attrs
import pytest
import sqlalchemy as sa
from pydantic import BaseModel
from pydantic_extra_types.color import Color

from anyschema._dependencies import (
    check_version,
    is_attrs_class,
    is_pydantic_base_model,
    is_pydantic_extra_types_color,
    is_sqlalchemy_table,
)


@pytest.mark.parametrize(
    ("package", "expected"),
    [
        ("annotated_types", True),
        ("not_a_library", False),
    ],
)
def test_check_version_no_min_version(package: str, *, expected: bool) -> None:
    assert check_version(package) is expected


@pytest.mark.parametrize(
    ("package", "installed_version"),
    [
        ("attrs", "22.1"),  # shorter version string should still pass
        ("attrs", "22.1.0"),
        ("attrs", "23.0.0"),
        ("pydantic", "2.0"),  # shorter version string should still pass
        ("pydantic", "2.0.0"),
        ("pydantic", "2.5.0"),
        ("sqlalchemy", "2.0"),  # shorter version string should still pass
        ("sqlalchemy", "2.0.0"),
        ("sqlalchemy", "2.1.0"),
    ],
)
def test_check_version_package_meets_minimum(package: str, installed_version: str) -> None:
    with patch("anyschema._dependencies.get_version", return_value=installed_version):
        assert check_version(package) is True


@pytest.mark.parametrize(
    ("package", "installed_version"),
    [
        ("attrs", "21.0.0"),
        ("pydantic", "1.10.0"),
        ("sqlalchemy", "1.4.0"),
    ],
)
def test_check_version_package_below_minimum_warns(package: str, installed_version: str) -> None:
    with (
        patch("anyschema._dependencies.get_version", return_value=installed_version),
        pytest.warns(UserWarning, match=rf"{package}.*{installed_version} is installed.*will ignore it") as record,
    ):
        result = check_version(package)

    assert result is False
    assert len(record) == 1


@pytest.mark.thread_unsafe(reason="patches module-level availability flags")
def test_specs_of_unavailable_libraries_are_not_detected() -> None:
    class PydanticModel(BaseModel):
        x: int

    @attrs.define
    class AttrsClass:
        x: int

    table = sa.Table("t", sa.MetaData(), sa.Column("x", sa.Integer))

    with patch.multiple(
        "anyschema._dependencies", PYDANTIC_AVAILABLE=False, ATTRS_AVAILABLE=False, SQLALCHEMY_AVAILABLE=False
    ):
        detected = (is_pydantic_base_model(PydanticModel), is_attrs_class(AttrsClass), is_sqlalchemy_table(table))

    assert detected == (False, False, False)


def test_is_pydantic_extra_types_color() -> None:
    assert is_pydantic_extra_types_color(Color)
    assert not is_pydantic_extra_types_color(str)
    assert not is_pydantic_extra_types_color("Color")


def test_is_pydantic_extra_types_color_module_not_imported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "pydantic_extra_types.color")
    assert not is_pydantic_extra_types_color(Color)
