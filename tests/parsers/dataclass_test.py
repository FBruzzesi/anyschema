from __future__ import annotations

from dataclasses import dataclass

import narwhals as nw
import pytest

from anyschema.parsers import ParserPipeline
from anyschema.parsers._builtin import PyTypeStep
from anyschema.parsers.dataclasses import DataclassTypeStep

# These are defined at module level as otherwise get_type_hints gets confused
# and treats Address as a ForwardRef. We could also fix this by removing
# from __future__ import annotations but I'm not sure what else that would affect

@dataclass
class Address:
    street: str
    city: str


@dataclass
class Person:
    name: str
    address: Address


@pytest.fixture(scope="module")
def dataclass_parser() -> DataclassTypeStep:
    """Create a PydanticTypeStep instance with pipeline set."""
    parser = DataclassTypeStep()
    py_parser = PyTypeStep()
    _ = ParserPipeline([parser, py_parser])
    return parser


def test_parse_nested_model(dataclass_parser: DataclassTypeStep) -> None:
    result = dataclass_parser.parse(Person, constraints=(), metadata={})

    address_fields = [
        nw.Field(name="street", dtype=nw.String()),
        nw.Field(name="city", dtype=nw.String()),
    ]
    expected_fields = [
        nw.Field(name="name", dtype=nw.String()),
        nw.Field(name="address", dtype=nw.Struct(address_fields)),
    ]
    expected = nw.Struct(expected_fields)

    assert result == expected
