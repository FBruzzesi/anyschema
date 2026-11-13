from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime  # noqa: TC003 (get_type_hints needs it at runtime)
from typing import TYPE_CHECKING, Mapping, Optional

import narwhals as nw
import pytest

from anyschema import AnySchema
from tests.conftest import DataclassEventWithTimeMetadata

if TYPE_CHECKING:
    from anyschema.typing import DataclassType


@dataclass
class Customer:
    name: str
    joined_at: datetime = field(metadata={"anyschema": {"time_zone": "UTC"}})


@dataclass
class Order:
    item: str
    customer: Customer
    referrer: Optional[Customer]
    co_buyers: list[Customer]


CUSTOMER_STRUCT = nw.Struct({"name": nw.String(), "joined_at": nw.Datetime("us", time_zone="UTC")})


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
        (
            Order,
            {
                "item": nw.String(),
                "customer": CUSTOMER_STRUCT,
                "referrer": CUSTOMER_STRUCT,
                "co_buyers": nw.List(CUSTOMER_STRUCT),
            },
        ),
    ],
)
def test_dataclass(spec: DataclassType, expected_schema: Mapping[str, nw.dtypes.DType]) -> None:
    schema = AnySchema(spec=spec)
    nw_schema = schema._nw_schema
    assert nw_schema == nw.Schema(expected_schema)
