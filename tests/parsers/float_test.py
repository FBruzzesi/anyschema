from __future__ import annotations

from typing import Optional

import hypothesis.strategies as st
import narwhals as nw
from hypothesis import assume
from hypothesis import given
from pydantic import BaseModel
from pydantic import FiniteFloat
from pydantic import NegativeFloat
from pydantic import NonNegativeFloat
from pydantic import NonPositiveFloat
from pydantic import PositiveFloat
from pydantic import confloat

from anyschema._parsers import model_to_nw_schema


@given(lb=st.floats(), ub=st.floats())
def test_parse_to_float(lb: float, ub: float) -> None:
    assume(lb < ub)

    class FloatModel(BaseModel):
        # python Float type
        py_int: float
        py_float_optional: Optional[float]  # noqa: UP007
        py_float_or_none: float | None
        py_none_or_float: None | float

        # pydantic NonNegativeFloat type
        non_negative: NonNegativeFloat
        non_negative_optional: Optional[NonNegativeFloat]  # noqa: UP007
        non_negative_or_none: NonNegativeFloat | None
        none_or_non_negative: None | NonNegativeFloat

        # pydantic NonPositiveFloat type
        non_positive: NonPositiveFloat
        non_positive_optional: Optional[NonPositiveFloat]  # noqa: UP007
        non_positive_or_none: NonPositiveFloat | None
        none_or_non_positive: None | NonPositiveFloat

        # pydantic PositiveFloat type
        positive: PositiveFloat
        positive_optional: Optional[PositiveFloat]  # noqa: UP007
        positive_or_none: PositiveFloat | None
        none_or_positive: None | PositiveFloat

        # pydantic NegativeFloat type
        negative: NegativeFloat
        negative_optional: Optional[NegativeFloat]  # noqa: UP007
        negative_or_none: NegativeFloat | None
        none_or_negative: None | NegativeFloat

        # pydantic NegativeFloat type
        finite: FiniteFloat
        finite_optional: Optional[FiniteFloat]  # noqa: UP007
        finite_or_none: FiniteFloat | None
        none_or_finite: None | NegativeFloat

        # pydantic confloat type
        con_float_optional: confloat(gt=lb, lt=ub)
        con_float_optional: Optional[confloat(ge=lb, lt=ub)]  # noqa: UP007
        con_float_or_none: confloat(gt=lb, le=ub) | None
        non_or_con_float: None | confloat(ge=lb, le=ub)

    schema = model_to_nw_schema(FloatModel)

    assert all(value == nw.Float64() for value in schema.values())
