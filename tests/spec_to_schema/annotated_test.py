from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, TypedDict

import attrs
import narwhals as nw
import pytest
from annotated_types import Ge, Lt

from anyschema import AnySchema

if TYPE_CHECKING:
    from anyschema.typing import Spec

UInt8Like = Annotated[int, Ge(0), Lt(256)]


@dataclass
class DataclassWithAnnotated:
    small: UInt8Like
    tagged: Annotated[str, "opaque marker"]


class TypedDictWithAnnotated(TypedDict):
    small: UInt8Like
    tagged: Annotated[str, "opaque marker"]


@attrs.define
class AttrsWithAnnotated:
    small: UInt8Like
    tagged: Annotated[str, "opaque marker"]


@dataclass
class DataclassWithNestedTypedDict:
    inner: TypedDictWithAnnotated


EXPECTED_STRUCT = nw.Struct({"small": nw.UInt8(), "tagged": nw.String()})


@pytest.mark.parametrize(
    ("spec", "expected_schema"),
    [
        (DataclassWithAnnotated, {"small": nw.UInt8(), "tagged": nw.String()}),
        (TypedDictWithAnnotated, {"small": nw.UInt8(), "tagged": nw.String()}),
        (AttrsWithAnnotated, {"small": nw.UInt8(), "tagged": nw.String()}),
        (DataclassWithNestedTypedDict, {"inner": EXPECTED_STRUCT}),
    ],
)
def test_annotated_fields_keep_constraints(spec: Spec, expected_schema: dict[str, nw.dtypes.DType]) -> None:
    """Regression test for #137: `Annotated` metadata must reach the pipeline, not be stripped by the adapter."""
    assert AnySchema(spec=spec)._nw_schema == nw.Schema(expected_schema)
