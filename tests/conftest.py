from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw
import pytest
from pydantic import BaseModel, PastDate, PositiveInt

from anyschema.parsers import make_pipeline

if TYPE_CHECKING:
    from anyschema.parsers import ParserPipeline


@pytest.fixture
def nw_schema() -> nw.Schema:
    return nw.Schema(
        {
            "array": nw.Array(nw.Int32(), 3),
            "boolean": nw.Boolean(),
            "categorical": nw.Categorical(),
            "date": nw.Date(),
            "datetime": nw.Datetime(),
            "decimal": nw.Decimal(),
            "duration": nw.Duration(),
            "enum": nw.Enum(["foo", "bar"]),
            "float32": nw.Float32(),
            "float64": nw.Float64(),
            "int8": nw.Int8(),
            "int16": nw.Int16(),
            "int32": nw.Int32(),
            "int64": nw.Int64(),
            "int128": nw.Int128(),
            "list": nw.List(nw.Float32()),
            "object": nw.Object(),
            "string": nw.String(),
            "struct": nw.Struct(fields=[nw.Field("field_1", nw.String()), nw.Field("field_2", nw.Boolean())]),
            "uint8": nw.UInt8(),
            "uint16": nw.UInt16(),
            "uint32": nw.UInt32(),
            "uint64": nw.UInt64(),
            "uint128": nw.UInt128(),
            "unknown": nw.Unknown(),
        }
    )


class Student(BaseModel):
    name: str
    date_of_birth: PastDate
    age: PositiveInt
    classes: list[str]
    has_graduated: bool


@pytest.fixture(scope="session")
def student_cls() -> type[Student]:
    return Student


@pytest.fixture(scope="session")
def auto_pipeline() -> ParserPipeline:
    """Fixture to get the auto pipeline."""
    return make_pipeline("auto")
