from __future__ import annotations

from datetime import datetime  # noqa: TC003

import narwhals as nw
from pydantic import BaseModel, FutureDatetime, NaiveDatetime, PastDatetime

from anyschema._pydantic import model_to_nw_schema
from anyschema.parsers import create_parser_chain

parser_chain = create_parser_chain("auto", model_type="pydantic")


def test_parse_datetime() -> None:
    class DatetimeModel(BaseModel):
        # python datetime type
        py_dt: datetime
        py_dt_optional: datetime | None
        py_dt_or_none: datetime | None
        none_or_py_dt: None | datetime

        # pydantic NaiveDatetime type
        naive_dt: NaiveDatetime
        naive_dt_optional: NaiveDatetime | None
        naive_dt_or_none: NaiveDatetime | None
        none_or_naive_dt: None | NaiveDatetime

        # pydantic PastDatetime type
        past_dt: PastDatetime
        past_dt_optional: PastDatetime | None
        past_dt_or_none: PastDatetime | None
        none_or_past_dt: None | PastDatetime

        # pydantic FutureDatetime type
        future_dt: FutureDatetime
        future_dt_optional: FutureDatetime | None
        future_dt_or_none: FutureDatetime | None
        none_or_future_dt: None | FutureDatetime

    schema = model_to_nw_schema(DatetimeModel, parser_chain=parser_chain)

    assert all(value == nw.Datetime() for value in schema.values())
