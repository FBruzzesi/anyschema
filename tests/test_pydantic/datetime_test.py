from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Optional

import narwhals as nw
import pytest
from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import FutureDatetime
from pydantic import NaiveDatetime
from pydantic import PastDatetime

from anyschema._pydantic import model_to_nw_schema
from anyschema.exceptions import UnsupportedDTypeError


def test_parse_datetime() -> None:
    class DatetimeModel(BaseModel):
        # python datetime type
        py_dt: datetime
        py_dt_optional: Optional[datetime]  # noqa: UP007
        py_dt_or_none: datetime | None
        none_or_py_dt: None | datetime

        # python NaiveDatetime type
        naive_dt: NaiveDatetime
        naive_dt_optional: Optional[NaiveDatetime]  # noqa: UP007
        naive_dt_or_none: NaiveDatetime | None
        none_or_naive_dt: None | NaiveDatetime

        # python PastDatetime type
        past_dt: PastDatetime
        past_dt_optional: Optional[PastDatetime]  # noqa: UP007
        past_dt_or_none: PastDatetime | None
        none_or_past_dt: None | PastDatetime

        # python FutureDatetime type
        future_dt: FutureDatetime
        future_dt_optional: Optional[FutureDatetime]  # noqa: UP007
        future_dt_or_none: FutureDatetime | None
        none_or_future_dt: None | FutureDatetime

    schema = model_to_nw_schema(DatetimeModel)

    assert all(value == nw.Datetime() for value in schema.values())


def test_raise_aware_datetime() -> None:
    class AwareDatetimeModel(BaseModel):
        aware_dt: AwareDatetime

    class OptAwareDatetimeModel(BaseModel):
        aware_dt: Optional[AwareDatetime]  # noqa: UP007

    class AwareDatetimeOrNoneModel(BaseModel):
        aware_dt: AwareDatetime | None

    class NoneOrAwareDatetimeModel(BaseModel):
        aware_dt: None | AwareDatetime

    with pytest.raises(UnsupportedDTypeError, match="pydantic AwareDatetime does not specify a fixed timezone."):
        model_to_nw_schema(AwareDatetimeModel)

    with pytest.raises(UnsupportedDTypeError, match="pydantic AwareDatetime does not specify a fixed timezone."):
        model_to_nw_schema(OptAwareDatetimeModel)

    with pytest.raises(UnsupportedDTypeError, match="pydantic AwareDatetime does not specify a fixed timezone."):
        model_to_nw_schema(AwareDatetimeOrNoneModel)

    with pytest.raises(UnsupportedDTypeError, match="pydantic AwareDatetime does not specify a fixed timezone."):
        model_to_nw_schema(NoneOrAwareDatetimeModel)
