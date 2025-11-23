from __future__ import annotations

from types import NoneType
from typing import Any, Optional, Union

import narwhals as nw
import pytest

from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers import ParserChain, PyTypeParser, UnionTypeParser


@pytest.fixture
def union_parser() -> UnionTypeParser:
    """Create a UnionTypeParser instance with parser_chain set."""
    union_parser = UnionTypeParser()
    py_parser = PyTypeParser()
    chain = ParserChain([union_parser, py_parser])
    union_parser.parser_chain = chain
    py_parser.parser_chain = chain
    return union_parser


@pytest.mark.parametrize(
    ("input_type", "expected"),
    [
        (Optional[int], nw.Int64()),
        (Optional[str], nw.String()),
        (Optional[float], nw.Float64()),
        (Optional[bool], nw.Boolean()),
        (int | None, nw.Int64()),
        (str | None, nw.String()),
        (None | int, nw.Int64()),
        (None | str, nw.String()),
        (Union[int, None], nw.Int64()),
        (Union[None, str], nw.String()),
        (Optional[list[int]], nw.List(nw.Int64())),
        (list[str] | None, nw.List(nw.String())),
        (list[str | None] | None, nw.List(nw.String())),
    ],
)
def test_parse_union_types(union_parser: UnionTypeParser, input_type: Any, expected: nw.dtypes.DType) -> None:
    result = union_parser.parse(input_type)
    assert result == expected


@pytest.mark.parametrize(
    "input_type",
    [
        int,
        str,
        list[int],
        NoneType,
    ],
)
def test_parse_non_union_types(union_parser: UnionTypeParser, input_type: Any) -> None:
    result = union_parser.parse(input_type)
    assert result is None


@pytest.mark.parametrize(
    ("input_type", "error_msg"),
    [
        (Union[int, str, float], "Union with more than two types is not supported."),
        (int | str | float, "Union with more than two types is not supported."),
        (Union[int, str], "Union with mixed types is not supported."),
        (int | str, "Union with mixed types is not supported."),
        (float | bool, "Union with mixed types is not supported."),
    ],
)
def test_parse_unsupported_unions_parametrized(union_parser: UnionTypeParser, input_type: Any, error_msg: str) -> None:
    with pytest.raises(UnsupportedDTypeError, match=error_msg):
        union_parser.parse(input_type)
