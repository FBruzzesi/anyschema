from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa

from anyschema import AnySchema

if TYPE_CHECKING:
    from pydantic import BaseModel


def test_to_arrow(student_cls: type[BaseModel]) -> None:
    anyschema = AnySchema(model=student_cls)
    pa_schema = anyschema.to_arrow()

    assert isinstance(pa_schema, pa.Schema)
    assert pa_schema == pa.schema(
        [
            ("name", pa.string()),
            ("age", pa.uint64()),
            ("classes", pa.list_(pa.string())),
        ]
    )
