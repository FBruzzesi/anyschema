from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from anyschema import AnySchema

if TYPE_CHECKING:
    from pydantic import BaseModel


def test_to_polars(student_cls: type[BaseModel]) -> None:
    anyschema = AnySchema(model=student_cls)
    pl_schema = anyschema.to_polars()

    assert isinstance(pl_schema, pl.Schema)
    assert pl_schema == pl.Schema(
        {
            "name": pl.String(),
            "age": pl.UInt64(),
            "classes": pl.List(pl.String()),
        }
    )
