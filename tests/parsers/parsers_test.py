from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Optional

import narwhals as nw
import pytest
from annotated_types import Gt
from pydantic import BaseModel, PositiveInt

from anyschema.parsers import (
    AnnotatedParser,
    ForwardRefParser,
    ParserChain,
    PyTypeParser,
    TypeParser,
    UnionTypeParser,
    create_parser_chain,
)
from anyschema.parsers.annotated_types import AnnotatedTypesParser
from anyschema.parsers.pydantic import PydanticTypeParser

if TYPE_CHECKING:
    from anyschema.typing import SpecType

PYDANTIC_CHAIN_CLS_ORDER = (
    ForwardRefParser,
    UnionTypeParser,
    AnnotatedParser,
    AnnotatedTypesParser,
    PydanticTypeParser,
    PyTypeParser,
)
PYTHON_CHAIN_CLS_ORDER = (ForwardRefParser, UnionTypeParser, AnnotatedParser, AnnotatedTypesParser, PyTypeParser)

PY_TYPE_PARSER = PyTypeParser()


class Address(BaseModel):
    street: str
    city: str


class Person(BaseModel):
    name: str
    address: Address


@pytest.mark.parametrize(
    ("spec_type", "expected_parsers"),
    [
        ("pydantic", PYDANTIC_CHAIN_CLS_ORDER),
        ("python", PYTHON_CHAIN_CLS_ORDER),
        (None, PYTHON_CHAIN_CLS_ORDER),
    ],
)
def test_create_parser_chain_auto(spec_type: SpecType, expected_parsers: tuple[type[TypeParser], ...]) -> None:
    chain = create_parser_chain("auto", spec_type=spec_type)
    assert isinstance(chain, ParserChain)
    assert len(chain.parsers) == len(expected_parsers)

    for _parser, _cls in zip(chain.parsers, expected_parsers, strict=True):
        assert isinstance(_parser, _cls)
        assert _parser.parser_chain is chain


@pytest.mark.parametrize(
    "parsers",
    [
        (PyTypeParser(),),
        (UnionTypeParser(), PyTypeParser()),
        (UnionTypeParser(), AnnotatedParser(), PyTypeParser()),
    ],
)
def test_create_parser_chain_custom(parsers: tuple[TypeParser, ...]) -> None:
    chain = create_parser_chain(parsers)
    assert isinstance(chain, ParserChain)
    assert len(chain.parsers) == len(parsers)

    for _chain_parser, _parser in zip(chain.parsers, parsers, strict=True):
        assert _parser is _chain_parser
        assert _parser.parser_chain is chain


@pytest.mark.parametrize(
    ("chain1", "chain2"),
    [
        (create_parser_chain("auto", spec_type="pydantic"), create_parser_chain("auto", spec_type="pydantic")),
        (create_parser_chain((PY_TYPE_PARSER,)), create_parser_chain((PY_TYPE_PARSER,))),
    ],
)
def test_caching(chain1: ParserChain, chain2: ParserChain) -> None:
    # Due to lru_cache, should be the same object
    assert chain1 is chain2

    chain3 = create_parser_chain("auto", spec_type="python")

    # Different parameters should create different chains
    assert chain1 is not chain3


@pytest.mark.parametrize(
    ("input_type", "spec_type", "expected"),
    [
        (int, "pydantic", nw.Int64()),
        (str, "pydantic", nw.String()),
        (list[int], "pydantic", nw.List(nw.Int64())),
        (Optional[int], "pydantic", nw.Int64()),
        (int, "python", nw.Int64()),
        (str, "python", nw.String()),
        (list[str], "python", nw.List(nw.String())),
        (Optional[float], "python", nw.Float64()),
        (Annotated[int, Gt(0)], "pydantic", nw.UInt64()),
        (PositiveInt, "pydantic", nw.UInt64()),
        (Optional[str], "python", nw.String()),
        (list[list[int]], "python", nw.List(nw.List(nw.Int64()))),
        (Optional[Annotated[int, Gt(0)]], "pydantic", nw.UInt64()),
        (Annotated[Optional[int], "metadata"], "pydantic", nw.Int64()),
        (Optional[list[int]], "pydantic", nw.List(nw.Int64())),
        (list[Optional[int]], "pydantic", nw.List(nw.Int64())),
    ],
)
def test_non_nested_parsing(input_type: type, spec_type: str, expected: nw.dtypes.DType) -> None:
    chain = create_parser_chain("auto", spec_type=spec_type)
    result = chain.parse(input_type)
    assert result == expected


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (Address, nw.Struct([nw.Field(name="street", dtype=nw.String()), nw.Field(name="city", dtype=nw.String())])),
        (
            Person,
            nw.Struct(
                [
                    nw.Field(name="name", dtype=nw.String()),
                    nw.Field(
                        name="address",
                        dtype=nw.Struct(
                            [
                                nw.Field(name="street", dtype=nw.String()),
                                nw.Field(name="city", dtype=nw.String()),
                            ]
                        ),
                    ),
                ]
            ),
        ),
    ],
)
def test_nested_parsing(input_type: type, expected: nw.dtypes.DType) -> None:
    chain = create_parser_chain("auto", spec_type="pydantic")
    result = chain.parse(input_type)
    assert result == expected
