from __future__ import annotations

from unittest.mock import patch

import pytest

from anyschema._dependencies import check_version


@pytest.mark.parametrize(
    ("package", "expected"),
    [
        ("annotated_types", True),
        ("not_a_library", False),
    ],
)
def test_check_version_no_min_version(package: str, *, expected: bool) -> None:
    """Test that _check_version returns False for non-existent packages."""
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
    """Test that _check_version returns True when version meets or exceeds minimum."""
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
def test_check_version_package_below_minimum_raises(package: str, installed_version: str) -> None:
    """Test that _check_version raises ImportError with helpful message when version is below minimum."""
    with (
        patch("anyschema._dependencies.get_version", return_value=installed_version),
        pytest.raises(ImportError) as exc_info,
    ):
        check_version(package)

    error_msg = str(exc_info.value)
    assert package in error_msg
    assert f"{installed_version} is installed" in error_msg
