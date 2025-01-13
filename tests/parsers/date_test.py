from __future__ import annotations

from datetime import date  # noqa: TC003
from typing import Optional

import hypothesis.strategies as st
import narwhals as nw
from hypothesis import assume
from hypothesis import given
from pydantic import BaseModel
from pydantic import FutureDate
from pydantic import PastDate
from pydantic import condate

from anyschema._parsers import model_to_nw_schema


def test_parse_date() -> None:
    class DateModel(BaseModel):
        # python datetime type
        py_dt: date
        py_dt_optional: Optional[date]  # noqa: UP007
        py_dt_or_none: date | None
        none_or_py_dt: None | date

        # python PastDate type
        past_dt: PastDate
        past_dt_optional: Optional[PastDate]  # noqa: UP007
        past_dt_or_none: PastDate | None
        none_or_past_dt: None | PastDate

        # python FutureDate type
        future_dt: FutureDate
        future_dt_optional: Optional[FutureDate]  # noqa: UP007
        future_dt_or_none: FutureDate | None
        none_or_future_dt: None | FutureDate

    schema = model_to_nw_schema(DateModel)

    assert all(value == nw.Date() for value in schema.values())


@given(min_date=st.dates(), max_date=st.dates())
def test_parse_condate(min_date: date, max_date: date) -> None:
    assume(min_date < max_date)

    class ConDateModel(BaseModel):
        x: condate(gt=min_date, lt=max_date)
        y: Optional[condate(ge=min_date, lt=max_date)]  # noqa: UP007
        z: condate(gt=min_date, le=max_date) | None
        w: None | condate(ge=min_date, le=max_date)

    schema = model_to_nw_schema(ConDateModel)

    assert all(value == nw.Date() for value in schema.values())
