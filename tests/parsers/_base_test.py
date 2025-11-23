# ruff: noqa: ARG002
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import narwhals as nw
import pytest

from anyschema.exceptions import UnavailablePipelineError
from anyschema.parsers import ParserPipeline, TypeParser

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


def test_pipeline_not_set() -> None:
    parser = AlwaysNoneParser()
    expected_msg = "`pipeline` is not set yet. You can set it by `parser.pipeline = chain"

    with pytest.raises(UnavailablePipelineError, match=expected_msg):
        _ = parser.pipeline


def test_pipeline_set_valid() -> None:
    parser = AlwaysNoneParser()
    chain = ParserPipeline([parser])
    parser.pipeline = chain

    assert parser.pipeline is chain


def test_pipeline_set_invalid_type() -> None:
    parser = AlwaysNoneParser()

    with pytest.raises(TypeError, match="Expected `ParserPipeline` object, found"):
        parser.pipeline = "not a chain"  # type: ignore[assignment]


def test_pipeline_setter_updates_correctly() -> None:
    parser = AlwaysNoneParser()
    chain1 = ParserPipeline([parser])
    chain2 = ParserPipeline([parser])

    parser.pipeline = chain1
    assert parser.pipeline is chain1

    parser.pipeline = chain2
    assert parser.pipeline is chain2


def test_pipeline_init_with_parsers() -> None:
    int_parser, str_parser = Int64Parser(), StrParser()
    parsers = [int_parser, str_parser]
    chain = ParserPipeline(parsers)

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
def test_pipeline_parse_non_strict(input_type: Any, expected: nw.dtypes.DType | None) -> None:
    chain = ParserPipeline([Int64Parser(), StrParser()])

    result = chain.parse(input_type, strict=False)
    assert result == expected


@pytest.mark.parametrize("input_type", [float, bool])
def test_pipeline_parse_strict(input_type: Any) -> None:
    chain = ParserPipeline([Int64Parser(), StrParser()])

    with pytest.raises(NotImplementedError, match="No parser in chain could handle type"):
        chain.parse(input_type, strict=True)


def test_pipeline_parse_with_metadata() -> None:
    parser = MetadataAwareParser()
    chain = ParserPipeline([parser])

    result = chain.parse(int, metadata=("meta1", "meta2"), strict=True)
    assert result == nw.Int32()

    result = chain.parse(int, metadata=("meta1",), strict=False)
    assert result is None


@pytest.mark.parametrize(
    ("parsers", "expected"),
    [((Int32Parser(), Int64Parser()), nw.Int32()), ((Int64Parser(), Int32Parser()), nw.Int64())],
)
def test_pipeline_parse_order_matters(parsers: tuple[TypeParser, ...], expected: nw.dtypes.DType) -> None:
    chain = ParserPipeline(parsers=parsers)
    result = chain.parse(int, strict=True)
    assert result == expected
