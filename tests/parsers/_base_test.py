# ruff: noqa: ARG002
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import narwhals as nw
import pytest

from anyschema.exceptions import UnavailableParseChainError
from anyschema.parsers import ParserChain, TypeParser

if TYPE_CHECKING:
    from narwhals.dtypes import DType


class AlwaysNoneParser(TypeParser):
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        return None


class StrParser(TypeParser):
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        return nw.String() if input_type is str else None


class Int32Parser(TypeParser):
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        return nw.Int32() if input_type is int else None


class Int64Parser(TypeParser):
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        return nw.Int64() if input_type is int else None


class MetadataAwareParser(TypeParser):
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        return nw.Int32() if input_type is int and metadata == ("meta1", "meta2") else None


def test_parser_chain_not_set() -> None:
    parser = AlwaysNoneParser()
    expected_msg = "`parser_chain` is not set yet. You can set it by `parser.parser_chain = chain"

    with pytest.raises(UnavailableParseChainError, match=expected_msg):
        _ = parser.parser_chain


def test_parser_chain_set_valid() -> None:
    parser = AlwaysNoneParser()
    chain = ParserChain([parser])
    parser.parser_chain = chain

    assert parser.parser_chain is chain


def test_parser_chain_set_invalid_type() -> None:
    parser = AlwaysNoneParser()

    with pytest.raises(TypeError, match="Expected `ParserChain` object, found"):
        parser.parser_chain = "not a chain"  # type: ignore[assignment]


def test_parser_chain_setter_updates_correctly() -> None:
    parser = AlwaysNoneParser()
    chain1 = ParserChain([parser])
    chain2 = ParserChain([parser])

    parser.parser_chain = chain1
    assert parser.parser_chain is chain1

    parser.parser_chain = chain2
    assert parser.parser_chain is chain2


def test_parser_chain_init_with_parsers() -> None:
    int_parser, str_parser = Int64Parser(), StrParser()
    parsers = [int_parser, str_parser]
    chain = ParserChain(parsers)

    assert len(chain.parsers) == len(parsers)
    assert chain.parsers == tuple(parsers)
    assert isinstance(chain.parsers, tuple)

    # Modifying the original list shouldn't affect the chain
    no_parser = AlwaysNoneParser()
    parsers.append(no_parser)
    assert len(chain.parsers) < len(parsers)


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (int, nw.Int64()),
        (str, nw.String()),
        (bool, None),
    ],
)
def test_parser_chain_parse_non_strict(input_type: Any, expected: nw.dtypes.DType | None) -> None:
    chain = ParserChain([Int64Parser(), StrParser()])

    result = chain.parse(input_type, strict=False)
    assert result == expected


@pytest.mark.parametrize("input_type", [float, bool])
def test_parser_chain_parse_strict(input_type: Any) -> None:
    chain = ParserChain([Int64Parser(), StrParser()])

    with pytest.raises(NotImplementedError, match="No parser in chain could handle type"):
        chain.parse(input_type, strict=True)


def test_parser_chain_parse_with_metadata() -> None:
    parser = MetadataAwareParser()
    chain = ParserChain([parser])

    result = chain.parse(int, metadata=("meta1", "meta2"), strict=True)
    assert result == nw.Int32()

    result = chain.parse(int, metadata=("meta1",), strict=False)
    assert result is None


@pytest.mark.parametrize(
    ("parsers", "expected"),
    [((Int32Parser(), Int64Parser()), nw.Int32()), ((Int64Parser(), Int32Parser()), nw.Int64())],
)
def test_parser_chain_parse_order_matters(parsers: tuple[TypeParser, ...], expected: nw.dtypes.DType) -> None:
    chain = ParserChain(parsers=parsers)
    result = chain.parse(int, strict=True)
    assert result == expected
