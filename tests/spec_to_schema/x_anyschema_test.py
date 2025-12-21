from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw
import pytest

from anyschema import AnySchema
from anyschema.parsers import ParserPipeline
from tests.conftest import AttrsEventWithXAnyschema, PydanticEventWithXAnyschema

if TYPE_CHECKING:
    from anyschema.typing import Spec


@pytest.mark.parametrize("spec", [AttrsEventWithXAnyschema, PydanticEventWithXAnyschema])
def test_spec_with_x_anyschema(spec: Spec) -> None:
    schema = AnySchema(spec=spec)

    assert schema.fields["created_at"].dtype == nw.Datetime(time_zone="UTC", time_unit="us")
    assert schema.fields["started_at"].dtype == nw.Datetime(time_unit="ms")


@pytest.mark.parametrize("metadata_key", ["anyschema", "x-anyschema"])
def test_dict_spec_with_both_prefixes(metadata_key: str) -> None:
    metadata = {metadata_key: {"nullable": True, "unique": True}}

    pipeline = ParserPipeline()
    field = pipeline.parse_into_field("test_field", int, (), metadata)

    assert field.nullable is True
    assert field.unique is True
