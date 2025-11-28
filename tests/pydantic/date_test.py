from __future__ import annotations

from datetime import date  # noqa: TC003
from typing import TYPE_CHECKING

import hypothesis.strategies as st
import narwhals as nw
from hypothesis import assume, given
from pydantic import BaseModel, FutureDate, PastDate, condate

from tests.pydantic.utils import model_to_nw_schema

if TYPE_CHECKING:
    from anyschema.parsers import ParserPipeline


def test_parse_date(auto_pipeline: ParserPipeline) -> None:
    class DateModel(BaseModel):
        # python datetime type
        py_dt: date
        py_dt_optional: date | None
        py_dt_or_none: date | None
        none_or_py_dt: None | date

        # pydantic PastDate type
        past_dt: PastDate
        past_dt_optional: PastDate | None
        past_dt_or_none: PastDate | None
        none_or_past_dt: None | PastDate

        # pydantic FutureDate type
        future_dt: FutureDate
        future_dt_optional: FutureDate | None
        future_dt_or_none: FutureDate | None
        none_or_future_dt: None | FutureDate

    schema = model_to_nw_schema(DateModel, pipeline=auto_pipeline)

    assert all(value == nw.Date() for value in schema.values())


@given(min_date=st.dates(), max_date=st.dates())
def test_parse_condate(auto_pipeline: ParserPipeline, min_date: date, max_date: date) -> None:
    assume(min_date < max_date)

    class ConDateModel(BaseModel):
        x: condate(gt=min_date, lt=max_date)
        y: condate(ge=min_date, lt=max_date) | None
        z: condate(gt=min_date, le=max_date) | None
        w: None | condate(ge=min_date, le=max_date)

    schema = model_to_nw_schema(ConDateModel, pipeline=auto_pipeline)

    assert all(value == nw.Date() for value in schema.values())
