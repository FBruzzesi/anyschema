from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Optional

import hypothesis.strategies as st
import narwhals as nw
from annotated_types import Interval
from hypothesis import assume, given
from pydantic import BaseModel, FiniteFloat, NegativeFloat, NonNegativeFloat, NonPositiveFloat, PositiveFloat

from tests.pydantic.utils import model_to_nw_schema

if TYPE_CHECKING:
    from anyschema.parsers import ParserPipeline


@given(lb=st.floats(), ub=st.floats())
def test_parse_float(auto_pipeline: ParserPipeline, lb: float, ub: float) -> None:
    assume(lb < ub)

    class FloatModel(BaseModel):
        # python float type
        py_int: float
        py_float_optional: float | None
        py_float_or_none: float | None
        none_or_py_float: float | None

        # pydantic NonNegativeFloat type
        non_negative: NonNegativeFloat
        non_negative_optional: NonNegativeFloat | None
        non_negative_or_none: NonNegativeFloat | None
        none_or_non_negative: NonNegativeFloat | None

        # pydantic NonPositiveFloat type
        non_positive: NonPositiveFloat
        non_positive_optional: NonPositiveFloat | None
        non_positive_or_none: NonPositiveFloat | None
        none_or_non_positive: NonPositiveFloat | None

        # pydantic PositiveFloat type
        positive: PositiveFloat
        positive_optional: PositiveFloat | None
        positive_or_none: PositiveFloat | None
        none_or_positive: PositiveFloat | None

        # pydantic NegativeFloat type
        negative: NegativeFloat
        negative_optional: NegativeFloat | None
        negative_or_none: NegativeFloat | None
        none_or_negative: NegativeFloat | None

        # pydantic NegativeFloat type
        finite: FiniteFloat
        finite_optional: FiniteFloat | None
        finite_or_none: FiniteFloat | None
        none_or_finite: NegativeFloat | None

        # pydantic annotated float with constraints
        con_float: Annotated[float, Interval(gt=lb, lt=ub)]
        con_float_optional: Optional[Annotated[float, Interval(ge=lb, lt=ub)]]
        con_float_or_none: Annotated[float, Interval(gt=lb, le=ub)] | None
        non_or_con_float: Annotated[float, Interval(ge=lb, le=ub)] | None

    schema = model_to_nw_schema(FloatModel, pipeline=auto_pipeline)

    assert all(value == nw.Float64() for value in schema.values())
