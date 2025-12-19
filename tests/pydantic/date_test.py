from __future__ import annotations

from datetime import date  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Optional

import hypothesis.strategies as st
import narwhals as nw
from annotated_types import Interval
from hypothesis import assume, given
from pydantic import BaseModel, FutureDate, PastDate

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
def test_parse_date_with_constraints(auto_pipeline: ParserPipeline, min_date: date, max_date: date) -> None:
    assume(min_date < max_date)

    class DateConstraintModel(BaseModel):
        x: Annotated[date, Interval(gt=min_date, lt=max_date)]
        y: Optional[Annotated[date, Interval(ge=min_date, lt=max_date)]] | None
        z: Annotated[date, Interval(gt=min_date, le=max_date)] | None
        w: None | Annotated[date, Interval(ge=min_date, le=max_date)]

    schema = model_to_nw_schema(DateConstraintModel, pipeline=auto_pipeline)

    assert all(value == nw.Date() for value in schema.values())
