from __future__ import annotations

from typing import Annotated

import narwhals as nw
import pytest

from anyschema.parsers import AnnotatedParser, ParserChain, PyTypeParser


@pytest.fixture(scope="module")
def annotated_parser() -> AnnotatedParser:
    """Create an AnnotatedParser instance with parser_chain set."""
    annotated_parser = AnnotatedParser()
    py_parser = PyTypeParser()
    chain = ParserChain([annotated_parser, py_parser])
    annotated_parser.parser_chain = chain
    py_parser.parser_chain = chain
    return annotated_parser


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (Annotated[int, "meta"], nw.Int64()),
        (Annotated[str, "meta"], nw.String()),
        (Annotated[float, "meta"], nw.Float64()),
        (Annotated[bool, "meta"], nw.Boolean()),
        (Annotated[list[int], "meta"], nw.List(nw.Int64())),
        (Annotated[list[str], "meta"], nw.List(nw.String())),
        (Annotated[tuple[int, ...], "meta"], nw.List(nw.Int64())),
        (Annotated[tuple[str, str, str], "meta"], nw.Array(nw.String(), shape=3)),
    ],
)
def test_parse_annotated(annotated_parser: AnnotatedParser, input_type: type, expected: nw.dtypes.DType) -> None:
    result = annotated_parser.parse(input_type)
    assert result == expected


@pytest.mark.parametrize(
    "metadata_items",
    [
        ("meta1",),
        ("meta1", "meta2"),
        ("meta1", "meta2", "meta3"),
        ({"key": "value"},),
        (["item1", "item2"],),
        (1, 2, 3),
    ],
)
def test_parse_annotated_various_metadata(annotated_parser: AnnotatedParser, metadata_items: tuple) -> None:
    """Parametrized test for Annotated with various metadata."""
    input_type = Annotated[int, metadata_items]
    result = annotated_parser.parse(input_type)
    assert result == nw.Int64()


@pytest.mark.parametrize("input_type", [int, str, list[int], tuple[str, ...]])
def test_parse_non_annotated(annotated_parser: AnnotatedParser, input_type: type) -> None:
    result = annotated_parser.parse(input_type)
    assert result is None


def test_parse_annotated_with_class_metadata(annotated_parser: AnnotatedParser) -> None:
    class CustomMetadata:
        def __init__(self, value: str) -> None:
            self.value = value

    result = annotated_parser.parse(Annotated[int, CustomMetadata("test")])
    assert result == nw.Int64()


def test_parse_annotated_with_callable_metadata(annotated_parser: AnnotatedParser) -> None:
    def validator(x: int) -> bool:
        return x > 0

    result = annotated_parser.parse(Annotated[int, validator])
    assert result == nw.Int64()
