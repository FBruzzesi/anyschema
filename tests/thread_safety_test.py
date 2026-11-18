"""Tests that always run in parallel threads (pytest-run-parallel), in every CI job.

Each test body runs in 8 threads that share the parametrize values, fixtures and module-level specs, the same way
users share a pipeline or a spec class across threads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, ForwardRef, Optional, TypedDict

import narwhals as nw
import pytest
from annotated_types import Ge
from pydantic import BaseModel, Field

from anyschema import AnySchema
from tests.conftest import AttrsPerson, PydanticStudent

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic.config import JsonDict

    from anyschema.parsers import ParserPipeline
    from anyschema.typing import FieldType

pytestmark = [pytest.mark.force_parallel_threads(8), pytest.mark.iterations(10)]

SHARED_EXTRA: JsonDict = {"anyschema": {"unique": True}}


@dataclass
class DataclassOrder:
    id: Annotated[int, Ge(0)]
    tags: list[str]
    note: str | None


class TypedDictOrder(TypedDict):
    id: int
    amounts: dict[str, float]


class PydanticSharedExtra(BaseModel):
    maybe: Optional[int] = Field(json_schema_extra=SHARED_EXTRA)
    always: int = Field(json_schema_extra=SHARED_EXTRA)


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (Annotated[int, Ge(0)], nw.UInt64()),
        (Optional[list[str]], nw.List(nw.String())),
        (ForwardRef("int"), nw.Int64()),
        (tuple[int, int], nw.Array(nw.Int64(), 2)),
    ],
)
def test_shared_pipeline_parse(auto_pipeline: ParserPipeline, input_type: FieldType, expected: nw.dtypes.DType) -> None:
    assert auto_pipeline.parse(input_type, (), {}, strict=True) == expected


@pytest.mark.parametrize("spec", [DataclassOrder, TypedDictOrder, PydanticStudent, AttrsPerson])
def test_shared_spec_to_schema(spec: type, thread_comp: Callable[..., None]) -> None:
    thread_comp(schema=AnySchema(spec=spec)._nw_schema)


def test_shared_nested_metadata_not_leaked() -> None:
    schema = AnySchema(spec=PydanticSharedExtra)

    assert schema.fields["maybe"].nullable is True
    assert schema.fields["always"].nullable is False
    assert SHARED_EXTRA == {"anyschema": {"unique": True}}
