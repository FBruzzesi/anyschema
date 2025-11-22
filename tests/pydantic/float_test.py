from __future__ import annotations

import hypothesis.strategies as st
import narwhals as nw
from hypothesis import assume, given
from pydantic import BaseModel, FiniteFloat, NegativeFloat, NonNegativeFloat, NonPositiveFloat, PositiveFloat, confloat

from anyschema.parsers import create_parser_chain
from tests.pydantic.utils import model_to_nw_schema

parser_chain = create_parser_chain("auto", spec_type="pydantic")


@given(lb=st.floats(), ub=st.floats())
def test_parse_float(lb: float, ub: float) -> None:
    assume(lb < ub)

    class FloatModel(BaseModel):
        # python float type
        py_int: float
        py_float_optional: float | None
        py_float_or_none: float | None
        none_or_py_float: None | float

        # pydantic NonNegativeFloat type
        non_negative: NonNegativeFloat
        non_negative_optional: NonNegativeFloat | None
        non_negative_or_none: NonNegativeFloat | None
        none_or_non_negative: None | NonNegativeFloat

        # pydantic NonPositiveFloat type
        non_positive: NonPositiveFloat
        non_positive_optional: NonPositiveFloat | None
        non_positive_or_none: NonPositiveFloat | None
        none_or_non_positive: None | NonPositiveFloat

        # pydantic PositiveFloat type
        positive: PositiveFloat
        positive_optional: PositiveFloat | None
        positive_or_none: PositiveFloat | None
        none_or_positive: None | PositiveFloat

        # pydantic NegativeFloat type
        negative: NegativeFloat
        negative_optional: NegativeFloat | None
        negative_or_none: NegativeFloat | None
        none_or_negative: None | NegativeFloat

        # pydantic NegativeFloat type
        finite: FiniteFloat
        finite_optional: FiniteFloat | None
        finite_or_none: FiniteFloat | None
        none_or_finite: None | NegativeFloat

        # pydantic confloat type
        con_float_optional: confloat(gt=lb, lt=ub)
        con_float_optional: confloat(ge=lb, lt=ub) | None
        con_float_or_none: confloat(gt=lb, le=ub) | None
        non_or_con_float: None | confloat(ge=lb, le=ub)

    schema = model_to_nw_schema(FloatModel, parser_chain=parser_chain)

    assert all(value == nw.Float64() for value in schema.values())
