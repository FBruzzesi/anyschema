from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import narwhals as nw
import pytest
from narwhals.schema import Schema

from anyschema import AnySchema
from anyschema.parsers import ParserPipeline, ParserStep, make_pipeline

if TYPE_CHECKING:
    from collections.abc import Callable

    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldSpecIterable, FieldType


class CustomType:
    pass


class CustomTypeStep(ParserStep):
    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,  # noqa: ARG002
        metadata: FieldMetadata,  # noqa: ARG002
    ) -> DType | None:
        return nw.String() if input_type is CustomType else None


def test_anyschema_with_unknown_spec_and_no_adapter() -> None:
    class UnknownClass:
        """A class that doesn't match any known adapter pattern."""

        some_field: int

    expected_msg = "`spec` type is unknown and `adapter` is not specified."
    with pytest.raises(ValueError, match=expected_msg):
        AnySchema(spec=UnknownClass)


def test_anyschema_with_unknown_spec_and_custom_adapter() -> None:
    class CustomSpec:
        """A custom spec class."""

        field1: str
        field2: int

    def custom_adapter(spec: CustomSpec) -> FieldSpecIterable:  # noqa: ARG001
        yield "field1", str, (), {}
        yield "field2", int, (), {}

    schema = AnySchema(spec=CustomSpec, adapter=custom_adapter)
    result = schema._nw_schema

    assert "field1" in result
    assert "field2" in result


def test_anyschema_custom_adapter_wins_over_auto_detection() -> None:
    from pydantic import BaseModel

    class Model(BaseModel):
        name: str

    def custom_adapter(spec: type[Model]) -> FieldSpecIterable:  # noqa: ARG001
        yield "other", int, (), {}

    schema = AnySchema(spec=Model, adapter=custom_adapter)

    assert schema.dtypes(named=True) == {"other": nw.Int64()}


def test_anyschema_with_narwhals_schema() -> None:
    nw_schema = Schema({"name": nw.String(), "age": nw.Int64()})
    anyschema = AnySchema(spec=nw_schema)
    assert anyschema._nw_schema is nw_schema


def test_anyschema_with_dict_spec() -> None:
    spec = {"name": str, "age": int}

    schema = AnySchema(spec=spec)
    result = schema._nw_schema

    assert "name" in result
    assert "age" in result


@pytest.mark.parametrize(
    "build_pipeline",
    [
        lambda: make_pipeline("auto").with_steps(CustomTypeStep()),
        lambda: ParserPipeline.from_auto(CustomTypeStep()),
        lambda: [step.clone() for step in ParserPipeline.from_auto(CustomTypeStep()).steps],
    ],
    ids=["with_steps", "from_auto", "cloned_steps"],
)
def test_anyschema_with_pipeline(build_pipeline: Callable[[], ParserPipeline | list[ParserStep]]) -> None:
    pipeline = build_pipeline()
    spec = {"custom_field": CustomType, "normal_field": int}
    schema = AnySchema(spec=spec, pipeline=pipeline)

    result = schema._nw_schema
    assert result == Schema(
        {
            "custom_field": nw.String(),
            "normal_field": nw.Int64(),
        }
    )


def test_spec_without_pydantic_or_sqlalchemy_types_does_not_import_them() -> None:
    # A fresh interpreter, since this test process already imported both libraries.
    code = (
        "import sys\n"
        "from typing import ForwardRef, Optional\n"
        "from anyschema import AnySchema\n"
        "AnySchema({'a': int, 'b': Optional[list[str]], 'c': ForwardRef('dict[str, float]')})\n"
        "print([name for name in ('pydantic', 'sqlalchemy') if name in sys.modules])\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)  # noqa: S603

    assert result.stdout.strip() == "[]"
