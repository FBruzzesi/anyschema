from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

import narwhals as nw
import pytest

from anyschema import AnySchema
from tests.conftest import DataclassEventWithTimeMetadata

if TYPE_CHECKING:
    from anyschema.typing import DataclassType


@pytest.mark.parametrize(
    ("spec", "expected_schema"),
    [
        (
            DataclassEventWithTimeMetadata,
            {
                "name": nw.String(),
                "created_at": nw.Datetime("us"),
                "scheduled_at": nw.Datetime("us", time_zone="UTC"),
                "started_at": nw.Datetime("ms"),
                "completed_at": nw.Datetime("ns", time_zone="Europe/Berlin"),
            },
        ),
    ],
)
def test_dataclass(spec: DataclassType, expected_schema: Mapping[str, nw.dtypes.DType]) -> None:
    schema = AnySchema(spec=spec)
    nw_schema = schema._nw_schema
    assert nw_schema == nw.Schema(expected_schema)
