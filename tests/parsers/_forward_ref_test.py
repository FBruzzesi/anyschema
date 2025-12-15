from __future__ import annotations

from typing import TYPE_CHECKING, Any, ForwardRef

import narwhals as nw
import pytest

from anyschema.parsers import ForwardRefStep, ParserPipeline, PyTypeStep, UnionTypeStep

if TYPE_CHECKING:
    from contextlib import AbstractContextManager


def forward_ref_parser_builder(globalns: dict | None = None, localns: dict | None = None) -> ForwardRefStep:
    forward_ref_parser = ForwardRefStep(globalns=globalns, localns=localns)
    union_parser = UnionTypeStep()
    py_parser = PyTypeStep()
    chain = ParserPipeline([forward_ref_parser, union_parser, py_parser])
    forward_ref_parser.pipeline = chain
    union_parser.pipeline = chain
    py_parser.pipeline = chain
    return forward_ref_parser


@pytest.fixture(scope="module")
def forward_ref_parser() -> ForwardRefStep:
    """Create a ForwardRefStep instance with pipeline set."""
    return forward_ref_parser_builder()


class CustomType:
    pass


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        ("int", nw.Int64()),
        ("str", nw.String()),
        ("float", nw.Float64()),
        ("bool", nw.Boolean()),
        ("list[int]", nw.List(nw.Int64())),
        ("list[str]", nw.List(nw.String())),
        ("tuple[int, ...]", nw.List(nw.Int64())),
        ("List[int]", nw.List(nw.Int64())),
        ("int | None", nw.Int64()),
        ("Optional[int]", nw.Int64()),
    ],
)
def test_forward_ref(forward_ref_parser: ForwardRefStep, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = forward_ref_parser.parse(input_type=ForwardRef(input_type), constraints=(), metadata={})
    assert result == expected


@pytest.mark.parametrize(
    "input_type",
    [
        int,
        str,
        list[int],
    ],
)
def test_non_forward_ref(forward_ref_parser: ForwardRefStep, input_type: Any) -> None:
    result = forward_ref_parser.parse(input_type=input_type, constraints=(), metadata={})
    assert result is None


def test_custom_globals() -> None:
    custom_globals = {
        "CustomType": int,  # Custom class to a parsable type
        "str": bool,  # don't do this in production
    }
    parser = forward_ref_parser_builder(globalns=custom_globals)
    result = parser.parse(ForwardRef("CustomType"), constraints=(), metadata={})
    assert result == nw.Int64()

    result = parser.parse(ForwardRef("str"), constraints=(), metadata={})
    assert result == nw.Boolean()


def test_custom_local() -> None:
    class LocalClass:
        pass

    parser = forward_ref_parser_builder(localns={"LocalClass": int})
    result = parser.parse(ForwardRef("LocalClass"), constraints=(), metadata={})
    assert result == nw.Int64()


@pytest.mark.parametrize(
    ("input_type", "context"),
    [
        ("UndefinedType", pytest.raises(NotImplementedError, match="Failed to resolve ForwardRef")),
        ("list[", pytest.raises(SyntaxError, match="Forward reference must be an expression")),
        ("1 + 1", pytest.raises(NotImplementedError, match="No parser in the pipeline could handle type")),
    ],
)
def test_resolution_error(
    forward_ref_parser: ForwardRefStep, input_type: str, context: AbstractContextManager[Any]
) -> None:
    with context:
        forward_ref_parser.parse(ForwardRef(input_type), constraints=(), metadata={})


def test_build_namespace_default(forward_ref_parser: ForwardRefStep) -> None:
    # Globals
    assert forward_ref_parser.globalns["int"] is int
    assert forward_ref_parser.globalns["str"] is str
    assert forward_ref_parser.globalns["float"] is float
    assert forward_ref_parser.globalns["bool"] is bool
    assert forward_ref_parser.globalns["list"] is list
    assert "Optional" in forward_ref_parser.globalns
    assert "Union" in forward_ref_parser.globalns
    assert "List" in forward_ref_parser.globalns

    # Locals
    assert forward_ref_parser.localns == {}


def test_build_namespace_custom() -> None:
    custom_globals = {"CustomType": CustomType, "MyInt": int, "bool": str}
    custom_locals = {"local_var": int}
    parser = forward_ref_parser_builder(globalns=custom_globals, localns=custom_locals)

    # Check that custom types are in the namespace
    assert parser.globalns["CustomType"] is CustomType
    assert parser.globalns["MyInt"] is int
    # Built-ins should still be there
    assert parser.globalns["int"] is int
    assert parser.globalns["str"] is str

    assert parser.globalns["bool"] is str

    assert parser.localns == custom_locals


def test_build_namespace_includes_pydantic_types() -> None:
    from anyschema._dependencies import PYDANTIC_AVAILABLE

    parser = forward_ref_parser_builder()

    if PYDANTIC_AVAILABLE:
        assert "BaseModel" in parser.globalns
        assert "Field" in parser.globalns
        assert "PositiveInt" in parser.globalns
        assert "NegativeInt" in parser.globalns
        assert "NonPositiveInt" in parser.globalns
        assert "NonNegativeInt" in parser.globalns
        assert "PositiveFloat" in parser.globalns
        assert "NegativeFloat" in parser.globalns
        assert "NonPositiveFloat" in parser.globalns
        assert "NonNegativeFloat" in parser.globalns
        assert "constr" in parser.globalns
        assert "conint" in parser.globalns
        assert "confloat" in parser.globalns
        assert "conlist" in parser.globalns
        assert "conset" in parser.globalns
    else:  # pragma: no cover
        ...


def test_build_namespace_includes_annotated_types() -> None:
    from anyschema._dependencies import ANNOTATED_TYPES_AVAILABLE

    parser = forward_ref_parser_builder()

    if ANNOTATED_TYPES_AVAILABLE:
        # Check that annotated_types are in the namespace
        assert "Gt" in parser.globalns
        assert "Ge" in parser.globalns
        assert "Lt" in parser.globalns
        assert "Le" in parser.globalns
        assert "Interval" in parser.globalns
        assert "MultipleOf" in parser.globalns
        assert "MinLen" in parser.globalns
        assert "MaxLen" in parser.globalns
        assert "Len" in parser.globalns
        assert "Timezone" in parser.globalns
        assert "Predicate" in parser.globalns
    else:  # pragma: no cover
        ...
