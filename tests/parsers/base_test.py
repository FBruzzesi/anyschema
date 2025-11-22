from __future__ import annotations

import pytest
from narwhals.dtypes import DType

from anyschema.exceptions import UnavailableParseChainError
from anyschema.parsers._base import ParserChain, TypeParser


class DummyParser(TypeParser):
    """A dummy parser for testing purposes."""

    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        """Parse only int types."""
        if input_type is int:
            import narwhals as nw

            return nw.Int64()
        return None


class AlwaysNoneParser(TypeParser):
    """A parser that always returns None."""

    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        """Always return None."""
        return None


class StrParser(TypeParser):
    """A parser that handles str types."""

    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        """Parse only str types."""
        if input_type is str:
            import narwhals as nw

            return nw.String()
        return None


def test_parser_chain_not_set() -> None:
    """Test that accessing parser_chain raises when not set."""
    parser = DummyParser()
    expected_msg = "`parser_chain` is not set yet. You can set it by `parser.parser_chain = chain"

    with pytest.raises(UnavailableParseChainError, match=expected_msg):
        _ = parser.parser_chain


def test_parser_chain_set_valid() -> None:
    """Test setting parser_chain with a valid ParserChain instance."""
    parser = DummyParser()
    chain = ParserChain([parser])
    parser.parser_chain = chain

    assert parser.parser_chain is chain


def test_parser_chain_set_invalid_type() -> None:
    """Test that setting parser_chain with invalid type raises TypeError."""
    parser = DummyParser()

    with pytest.raises(TypeError, match="Expected `ParserChain` object, found"):
        parser.parser_chain = "not a chain"  # type: ignore[assignment]


def test_parser_chain_setter_updates_correctly() -> None:
    """Test that parser_chain can be updated."""
    parser = DummyParser()
    chain1 = ParserChain([parser])
    chain2 = ParserChain([parser])

    parser.parser_chain = chain1
    assert parser.parser_chain is chain1

    parser.parser_chain = chain2
    assert parser.parser_chain is chain2


def test_parser_chain_init_with_parsers() -> None:
    """Test ParserChain initialization with a list of parsers."""
    parser1 = DummyParser()
    parser2 = StrParser()
    chain = ParserChain([parser1, parser2])

    assert len(chain.parsers) == 2
    assert chain.parsers[0] is parser1
    assert chain.parsers[1] is parser2


def test_parser_chain_init_converts_to_tuple() -> None:
    """Test that ParserChain converts parsers list to tuple."""
    parser1 = DummyParser()
    parsers_list = [parser1]
    chain = ParserChain(parsers_list)

    assert isinstance(chain.parsers, tuple)
    # Modifying the original list shouldn't affect the chain
    parsers_list.append(StrParser())
    assert len(chain.parsers) == 1


def test_parser_chain_parse_first_parser_matches() -> None:
    """Test that parse returns result from first matching parser."""
    import narwhals as nw

    parser1 = DummyParser()
    parser2 = StrParser()
    chain = ParserChain([parser1, parser2])

    result = chain.parse(int, strict=True)
    assert result == nw.Int64()


def test_parser_chain_parse_second_parser_matches() -> None:
    """Test that parse tries parsers in sequence."""
    import narwhals as nw

    parser1 = AlwaysNoneParser()
    parser2 = StrParser()
    chain = ParserChain([parser1, parser2])

    result = chain.parse(str, strict=True)
    assert result == nw.String()


def test_parser_chain_parse_no_parser_matches_strict_true() -> None:
    """Test that parse raises NotImplementedError when strict=True and no parser matches."""
    parser1 = DummyParser()
    parser2 = StrParser()
    chain = ParserChain([parser1, parser2])

    with pytest.raises(NotImplementedError, match="No parser in chain could handle type"):
        chain.parse(float, strict=True)


def test_parser_chain_parse_no_parser_matches_strict_false() -> None:
    """Test that parse returns None when strict=False and no parser matches."""
    parser1 = DummyParser()
    parser2 = StrParser()
    chain = ParserChain([parser1, parser2])

    result = chain.parse(float, strict=False)
    assert result is None


def test_parser_chain_parse_with_metadata() -> None:
    """Test that parse passes metadata to parsers correctly."""
    import narwhals as nw

    class MetadataAwareParser(TypeParser):
        def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
            if input_type is int and metadata == ("meta1", "meta2"):
                return nw.Int32()
            return None

    parser = MetadataAwareParser()
    chain = ParserChain([parser])

    result = chain.parse(int, metadata=("meta1", "meta2"), strict=True)
    assert result == nw.Int32()


def test_parser_chain_parse_default_strict_true() -> None:
    """Test that strict defaults to True."""
    parser = AlwaysNoneParser()
    chain = ParserChain([parser])

    with pytest.raises(NotImplementedError):
        chain.parse(int)


def test_parser_chain_parse_empty_metadata_default() -> None:
    """Test that metadata defaults to empty tuple."""
    import narwhals as nw

    parser = DummyParser()
    chain = ParserChain([parser])

    result = chain.parse(int, strict=True)
    assert result == nw.Int64()


def test_parser_chain_parse_order_matters() -> None:
    """Test that parser order matters - first match wins."""
    import narwhals as nw

    class Int32Parser(TypeParser):
        def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
            if input_type is int:
                return nw.Int32()
            return None

    class Int64Parser(TypeParser):
        def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
            if input_type is int:
                return nw.Int64()
            return None

    # First parser wins
    chain1 = ParserChain([Int32Parser(), Int64Parser()])
    result1 = chain1.parse(int, strict=True)
    assert result1 == nw.Int32()

    # Order reversed - other parser wins
    chain2 = ParserChain([Int64Parser(), Int32Parser()])
    result2 = chain2.parse(int, strict=True)
    assert result2 == nw.Int64()
