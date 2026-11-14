from __future__ import annotations

import sys
from dataclasses import dataclass, make_dataclass
from dataclasses import field as dc_field
from typing import TYPE_CHECKING, Annotated, Any, Literal, Optional, cast

import attrs
import narwhals as nw
import pytest
from annotated_types import Gt
from pydantic import BaseModel, Field, create_model
from typing_extensions import TypedDict

from anyschema import AnyField, AnySchema, WithAnySchema

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import Spec

SpecKind = Literal["dict", "typed_dict", "dataclass", "attrs", "pydantic"]
ALL_KINDS: tuple[SpecKind, ...] = ("dict", "typed_dict", "dataclass", "attrs", "pydantic")
KINDS_WITH_METADATA: tuple[SpecKind, ...] = ("dataclass", "attrs", "pydantic")


def make_spec(kind: SpecKind, tp: Any, metadata: dict[str, Any] | None = None, name: str = "x") -> Spec:
    """Build a one-field spec of the given kind; `metadata` is the spec's own (adapter-provided) field metadata."""
    if kind == "dict":
        assert metadata is None
        return {name: tp}
    if kind == "typed_dict":
        assert metadata is None
        return TypedDict("TD", {name: tp})  # type: ignore[operator]
    if kind == "dataclass":
        return make_dataclass("DC", [(name, tp, dc_field(metadata=metadata or {}))])
    if kind == "attrs":
        return attrs.make_class("AT", {name: attrs.field(type=tp, metadata=metadata or {})})
    return cast("Any", create_model)("PD", **{name: (tp, Field(json_schema_extra=metadata))})


def field_of(spec: Spec, name: str = "x") -> AnyField:
    return AnySchema(spec=spec).fields[name]


# --- Basic behaviour ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize("into_dtype", [nw.Int32(), "Int32"])
def test_with_anyschema_dtype_overrides_dtype(kind: SpecKind, into_dtype: DType | str) -> None:
    field = field_of(make_spec(kind, Annotated[int, WithAnySchema(dtype=into_dtype)]))
    assert field == AnyField(name="x", dtype=nw.Int32())


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_with_anyschema_feeds_field(kind: SpecKind) -> None:
    marker = WithAnySchema(unique=True, description="desc", nullable=True, custom={"foo": "bar"})
    field = field_of(make_spec(kind, Annotated[str, marker]))
    assert field == AnyField(
        name="x", dtype=nw.String(), nullable=True, unique=True, description="desc", metadata={"foo": "bar"}
    )


# --- Composition: repeated markers, last wins --------------------------------------------------------------------

LibEmail = Annotated[str, WithAnySchema(description="lib", unique=True, custom={"owner": "lib"})]


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_library_alias_then_user_marker(kind: SpecKind) -> None:
    tp = Annotated[LibEmail, WithAnySchema(description="mine", custom={"owner": "me"})]
    field = field_of(make_spec(kind, tp))
    # `description` and `owner` overridden by the user; `unique` kept from the library.
    assert field == AnyField(name="x", dtype=nw.String(), unique=True, description="mine", metadata={"owner": "me"})


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_duplicate_markers_in_one_annotated(kind: SpecKind) -> None:
    tp = Annotated[
        int,
        WithAnySchema(dtype=nw.Int8()),
        WithAnySchema(custom={"foo": {"a": 1}, "keep": 1}),
        WithAnySchema(dtype=nw.Int16()),
        WithAnySchema(custom={"foo": {"b": 2}}),
    ]
    field = field_of(make_spec(kind, tp))
    # Custom keys are shallow-merged: `foo` is replaced as a whole.
    assert field == AnyField(name="x", dtype=nw.Int16(), metadata={"foo": {"b": 2}, "keep": 1})


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize(
    ("tp", "expected"),
    [
        (Annotated[int, WithAnySchema(dtype="Int8"), WithAnySchema(dtype="Int16")], nw.Int16()),
        (Annotated[int, WithAnySchema(dtype="Int16"), WithAnySchema(dtype="Int8")], nw.Int8()),
        (Annotated[int, WithAnySchema(dtype="Int16"), WithAnySchema()], nw.Int16()),
    ],
)
def test_with_anyschema_last_dtype_wins(kind: SpecKind, tp: Any, expected: DType) -> None:
    assert field_of(make_spec(kind, tp)).dtype == expected


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_inner_layer_before_outer_layer(kind: SpecKind) -> None:
    # For Pydantic the outer marker becomes a constraint, the inner one stays in the annotation.
    tp = Annotated[
        Annotated[int, WithAnySchema(description="inner", unique=True)] | None,
        WithAnySchema(description="outer"),
    ]
    field = field_of(make_spec(kind, tp))
    assert field == AnyField(name="x", dtype=nw.Int64(), nullable=True, unique=True, description="outer")


def test_pydantic_marker_alongside_field_constraint() -> None:
    class Model(BaseModel):
        x: Annotated[int, WithAnySchema(unique=True), Field(ge=0), WithAnySchema(dtype="Int32")]
        y: Annotated[int, Field(ge=0), WithAnySchema(custom={"foo": 1})]

    schema = AnySchema(spec=Model)
    assert schema.fields["x"] == AnyField(name="x", dtype=nw.Int32(), unique=True)
    assert schema.fields["y"] == AnyField(name="y", dtype=nw.UInt64(), metadata={"foo": 1})


# --- Conflicts across sources ------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS_WITH_METADATA)
@pytest.mark.parametrize(
    ("marker", "spec_metadata", "keys"),
    [
        (WithAnySchema(unique=True), {"anyschema": {"unique": True}}, "'unique'"),
        (WithAnySchema(unique=True), {"x-anyschema": {"unique": False}}, "'unique'"),
        (WithAnySchema(custom={"foo": "bar"}), {"foo": "bar"}, "'foo'"),
        (WithAnySchema(dtype="Int32"), {"anyschema": {"dtype": "Int32"}}, "'dtype'"),
        (WithAnySchema(dtype="Int32"), {"anyschema": {"dtype": "Int64"}}, "'dtype'"),
        (
            WithAnySchema(unique=True, nullable=True, custom={"foo": 1}),
            {"foo": 1, "bar": 2, "anyschema": {"nullable": True}},
            "'nullable', 'foo'",
        ),
    ],
)
def test_conflict_with_spec_metadata_raises(
    kind: SpecKind, marker: WithAnySchema, spec_metadata: dict[str, Any], keys: str
) -> None:
    spec = make_spec(kind, Annotated[int, marker], metadata=spec_metadata, name="my_field")
    with pytest.raises(ValueError, match=rf"field 'my_field'.*: {keys}\."):
        AnySchema(spec=spec)


def test_conflict_with_pydantic_description_raises() -> None:
    class Model(BaseModel):
        x: Annotated[int, WithAnySchema(description="marker")] = Field(description="pydantic")

    with pytest.raises(ValueError, match=r"field 'x'.*: 'description'\."):
        AnySchema(spec=Model)


@pytest.mark.parametrize("kind", KINDS_WITH_METADATA)
@pytest.mark.parametrize("namespace", ["anyschema", "x-anyschema"])
def test_no_conflict_on_disjoint_keys(kind: SpecKind, namespace: str) -> None:
    spec_metadata = {namespace: {"description": "spec"}, "foo": 1}
    spec = make_spec(kind, Annotated[int, WithAnySchema(unique=True, custom={"bar": 2})], spec_metadata)
    field = field_of(spec)
    assert field == AnyField(name="x", dtype=nw.Int64(), unique=True, description="spec", metadata={"foo": 1, "bar": 2})
    # The spec's own metadata is never mutated.
    assert spec_metadata == {namespace: {"description": "spec"}, "foo": 1}


@pytest.mark.skipif(sys.version_info < (3, 14), reason="dataclass `doc` was added in Python 3.14")
def test_conflict_with_dataclass_doc_raises() -> None:
    spec = make_dataclass("DC", [("x", Annotated[int, WithAnySchema(description="marker")], dc_field(doc="doc"))])  # type: ignore[call-arg, unused-ignore]

    with pytest.raises(ValueError, match=r"field 'x'.*: 'description'\."):
        AnySchema(spec=spec)


def test_user_metadata_dict_not_aliased() -> None:
    raw: dict[str, Any] = {"foo": {"bar": 1}}
    marker = WithAnySchema(custom=raw)
    AnySchema(spec={"x": Optional[Annotated[int, marker]]})
    assert raw == {"foo": {"bar": 1}}
    raw["foo"] = 2
    assert marker.custom == {"foo": {"bar": 1}}


# --- Placement and nullability -----------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize(
    "tp",
    [
        Annotated[int, WithAnySchema(dtype=nw.Int32())] | None,  # pyright: ignore[reportOperatorIssue]
        Optional[Annotated[int, WithAnySchema(dtype=nw.Int32())]],
        Annotated[int | None, WithAnySchema(dtype=nw.Int32())],
        Annotated[Optional[int], WithAnySchema(dtype="Int32")],
        Annotated[Annotated[int, WithAnySchema(dtype=nw.Int8())] | None, WithAnySchema(dtype=nw.Int32())],
    ],
)
def test_dtype_and_optional_is_nullable(kind: SpecKind, tp: Any) -> None:
    assert field_of(make_spec(kind, tp)) == AnyField(name="x", dtype=nw.Int32(), nullable=True)


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize("nullable", [True, False])
def test_dtype_explicit_nullable_wins(kind: SpecKind, *, nullable: bool) -> None:
    tp = Annotated[int | None, WithAnySchema(dtype=nw.Int32()), WithAnySchema(nullable=nullable)]
    assert field_of(make_spec(kind, tp)).nullable is nullable


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_explicit_not_nullable_wins_without_dtype(kind: SpecKind) -> None:
    tp = Annotated[int | None, WithAnySchema(nullable=False)]
    assert field_of(make_spec(kind, tp)) == AnyField(name="x", dtype=nw.Int64(), nullable=False)


@pytest.mark.parametrize("kind", KINDS_WITH_METADATA)
def test_dtype_spec_nullable_wins(kind: SpecKind) -> None:
    spec = make_spec(
        kind, Annotated[int | None, WithAnySchema(dtype=nw.Int32())], metadata={"anyschema": {"nullable": False}}
    )
    assert field_of(spec) == AnyField(name="x", dtype=nw.Int32(), nullable=False)


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_optional_without_dtype(kind: SpecKind) -> None:
    tp = Annotated[Annotated[int, Gt(0)] | None, WithAnySchema(custom={"foo": 1})]
    assert field_of(make_spec(kind, tp)) == AnyField(name="x", dtype=nw.UInt64(), nullable=True, metadata={"foo": 1})


@pytest.mark.parametrize("kind", KINDS_WITH_METADATA)
def test_spec_dtype_override_does_not_infer_nullable(kind: SpecKind) -> None:
    # Existing `dtype` override from the spec's own metadata is unchanged: no nullability inference.
    spec = make_spec(kind, int | None, metadata={"anyschema": {"dtype": "Int32"}})
    assert field_of(spec) == AnyField(name="x", dtype=nw.Int32(), nullable=False)


# --- Nested markers ----------------------------------------------------------------------------------------------


class InnerTD(TypedDict):
    a: Annotated[int, WithAnySchema(dtype=nw.Int8())]
    b: Annotated[str, WithAnySchema(dtype=nw.Categorical())] | None


class InnerModel(BaseModel):
    a: Annotated[int, WithAnySchema(dtype=nw.Int8())]
    b: Annotated[str, WithAnySchema(dtype=nw.Categorical())] | None


@dataclass
class InnerDC:
    a: Annotated[int, WithAnySchema(dtype=nw.Int8())]
    b: Annotated[str, WithAnySchema(dtype=nw.Categorical())] | None


INNER_STRUCT = nw.Struct({"a": nw.Int8(), "b": nw.Categorical()})


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize(
    ("tp", "expected"),
    [
        (list[Annotated[str, WithAnySchema(dtype=nw.Categorical())]], nw.List(nw.Categorical())),
        (list[Annotated[int, Gt(0), WithAnySchema(dtype="Int8")]], nw.List(nw.Int8())),
        (list[Annotated[int, WithAnySchema(dtype="Int8"), WithAnySchema(dtype="Int16")]], nw.List(nw.Int16())),
        (list[Annotated[int, WithAnySchema(dtype="Int8"), WithAnySchema()]], nw.List(nw.Int8())),
        (Annotated[list[Annotated[str, WithAnySchema(dtype=nw.Categorical())]], Gt(0)], nw.List(nw.Categorical())),
        (InnerTD, INNER_STRUCT),
        (InnerModel, INNER_STRUCT),
        (InnerDC, INNER_STRUCT),
    ],
)
def test_nested_dtype(kind: SpecKind, tp: Any, expected: DType) -> None:
    assert field_of(make_spec(kind, tp)).dtype == expected


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize(
    "tp",
    [
        list[Annotated[str, WithAnySchema(custom={"foo": 1})]],
        list[Annotated[str, WithAnySchema(dtype="String", unique=True)]],
        Annotated[list[Annotated[str, WithAnySchema(custom={"foo": 1})]], WithAnySchema(custom={"bar": 2})],
        # Second `| None` layer is not field level
        Annotated[
            Annotated[Annotated[int, WithAnySchema(custom={"foo": 1})] | None, Gt(0)] | None,
            WithAnySchema(custom={"bar": 2}),
        ],
    ],
)
def test_nested_non_dtype_raises(kind: SpecKind, tp: Any) -> None:
    with pytest.raises(NotImplementedError, match="Nested `WithAnySchema` markers can only set `dtype`"):
        AnySchema(spec=make_spec(kind, tp))


def test_nested_struct_field_non_dtype_raises() -> None:
    class Inner(BaseModel):
        a: Annotated[int, WithAnySchema(custom={"foo": 1})]

    with pytest.raises(NotImplementedError, match="Nested `WithAnySchema` markers can only set `dtype`"):
        AnySchema(spec={"x": Inner})


# --- Regressions for existing `Annotated` constraints ------------------------------------------------------------


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize(
    ("tp", "expected"),
    [
        (Annotated[int, Gt(0)], nw.UInt64()),
        (Annotated[int, Gt(0), WithAnySchema(custom={"foo": 1})], nw.UInt64()),
        (Annotated[int, WithAnySchema(custom={"foo": 1}), Gt(0)], nw.UInt64()),
        (Annotated[int, Gt(0), WithAnySchema(dtype="Int8")], nw.Int8()),
    ],
)
def test_existing_constraints_still_apply(kind: SpecKind, tp: Any, expected: DType) -> None:
    assert field_of(make_spec(kind, tp)).dtype == expected
