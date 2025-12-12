from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

import narwhals as nw
import pytest

from anyschema import AnySchema
from tests.conftest import (
    AttrsAddressWithPydantic,
    AttrsDerived,
    AttrsEventWithTimeMetadata,
    AttrsPerson,
    AttrsPersonWithLiterals,
    create_missing_decorator_test_case,
)

if TYPE_CHECKING:
    from anyschema.typing import AttrsClassType


@pytest.mark.parametrize(
    ("spec", "expected_schema"),
    [
        (
            AttrsPerson,
            {
                "name": nw.String(),
                "age": nw.Int64(),
                "date_of_birth": nw.Date(),
                "is_active": nw.Boolean(),
                "classes": nw.List(nw.String()),
                "grades": nw.List(nw.Float64()),
            },
        ),
        (
            AttrsPersonWithLiterals,
            {
                "username": nw.String(),
                "role": nw.Enum(["admin", "user", "guest"]),
                "status": nw.Enum(["active", "inactive", "pending"]),
            },
        ),
        (
            AttrsAddressWithPydantic,
            {
                "street": nw.String(),
                "city": nw.String(),
                "zipcode": nw.Struct([nw.Field("zipcode", nw.UInt64())]),
            },
        ),
        (
            AttrsDerived,
            {
                "foo": nw.String(),
                "bar": nw.Int64(),
                "baz": nw.Float64(),
            },
        ),
        (
            AttrsEventWithTimeMetadata,
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
def test_attrs_class(spec: AttrsClassType, expected_schema: Mapping[str, nw.dtypes.DType]) -> None:
    schema = AnySchema(spec=spec)
    nw_schema = schema._nw_schema
    assert nw_schema == nw.Schema(expected_schema)


def test_attrs_class_missing_decorator_raises() -> None:
    child_cls, expected_msg = create_missing_decorator_test_case()
    with pytest.raises(AssertionError, match=expected_msg.replace("(", r"\(").replace(")", r"\)")):
        AnySchema(spec=child_cls)
