from __future__ import annotations

from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest
from marshmallow import Schema, fields

from anyschema.adapters import marshmallow_adapter

if TYPE_CHECKING:
    from anyschema.typing import FieldMetadata, FieldSpec

EMPTY_METADATA: FieldMetadata = {}  # Type hinted empty metadata dict


class AddressSchema(Schema):
    street = fields.String()
    city = fields.String()


class StudentSchema(Schema):
    id = fields.Integer(metadata={"anyschema": {"description": "User ID"}})
    name = fields.String()
    age = fields.Integer()
    birth_date = fields.Date()
    email = fields.Email(metadata={"format": "email"})
    address = fields.Nested(AddressSchema)
    created_at = fields.AwareDateTime(
        default_timezone=ZoneInfo("Europe/Berlin"), metadata={"anyschema": {"time_unit": "ms"}}
    )
    registered_at = fields.AwareDateTime(metadata={"anyschema": {"time_zone": "UTC"}})
    classes = fields.List(fields.String())


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (
            StudentSchema,
            (
                (
                    "id",
                    fields.Integer(metadata={"anyschema": {"description": "User ID"}}),
                    (),
                    {"anyschema": {"description": "User ID", "nullable": False}},
                ),
                ("name", fields.String(), (), {"anyschema": {"nullable": False}}),
                ("age", fields.Integer(), (), {"anyschema": {"nullable": False}}),
                ("birth_date", fields.Date(), (), {"anyschema": {"nullable": False}}),
                ("email", fields.Email(metadata={"format": "email"}), (), {"format": "email"}),
                ("address", fields.Nested(AddressSchema), (), {"anyschema": {"nullable": False}}),
                (
                    "created_at",
                    fields.AwareDateTime(
                        default_timezone=ZoneInfo("Europe/Berlin"), metadata={"anyschema": {"time_unit": "ms"}}
                    ),
                    (),
                    {"anyschema": {"time_zone": "Europe/Berlin", "time_unit": "ms"}},
                ),
                (
                    "registered_at",
                    fields.AwareDateTime(metadata={"anyschema": {"time_zone": "UTC"}}),
                    (),
                    {"anyschema": {"time_zone": "UTC"}},
                ),
                ("classes", fields.List(fields.String()), (), {"anyschema": {"nullable": False}}),
            ),
        )
    ],
)
def test_marshmallow_adapter(spec: type[Schema], expected: tuple[FieldSpec, ...]) -> None:
    result = tuple(marshmallow_adapter(spec))
    breakpoint()
    assert result == expected
