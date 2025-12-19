from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from anyschema.adapters import into_ordered_dict_adapter

if TYPE_CHECKING:
    from anyschema.typing import FieldSpec, IntoOrderedDict


@pytest.mark.parametrize(
    "spec",
    [
        {"name": str, "age": int},
        [("name", str), ("age", int)],
    ],
)
def test_into_ordered_dict_adapter(spec: IntoOrderedDict) -> None:
    expected: tuple[FieldSpec, ...] = (("name", str, (), {}), ("age", int, (), {}))
    result = tuple(into_ordered_dict_adapter(spec))
    assert result == expected
