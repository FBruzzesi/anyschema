from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Annotated, Any, Optional, Union

import narwhals as nw
import pytest
from annotated_types import Gt

from anyschema import WithAnySchema
from anyschema.exceptions import UnsupportedDTypeError
from anyschema.parsers._annotated import field_contains_none, split_field_markers


@pytest.mark.parametrize(
    ("into_dtype", "expected"),
    [
        (nw.Int32(), nw.Int32()),
        ("Int32", nw.Int32()),
        ("List(String)", nw.List(nw.String())),
        (nw.Datetime("ms", "UTC"), nw.Datetime("ms", "UTC")),
    ],
)
def test_with_anyschema_deserializes_dtype(into_dtype: nw.dtypes.DType | str, expected: nw.dtypes.DType) -> None:
    marker = WithAnySchema(dtype=into_dtype)
    assert marker.dtype == expected
    assert marker == WithAnySchema(dtype=expected)


def test_with_anyschema_construction() -> None:
    marker = WithAnySchema(unique=True, dtype="Int32", custom={"foo": "bar"})
    assert marker.anyschema == {"unique": True, "dtype": nw.Int32()}
    assert marker.custom == {"foo": "bar"}
    assert repr(marker) == "WithAnySchema(unique=True, dtype=Int32, custom={'foo': 'bar'})"
    assert repr(WithAnySchema()) == "WithAnySchema()"
    assert WithAnySchema(unique=True).dtype is None


def test_with_anyschema_copies_custom() -> None:
    custom: dict[str, Any] = {"foo": "bar"}
    marker = WithAnySchema(custom=custom)
    custom["foo"] = "changed"
    assert marker.custom == {"foo": "bar"}


@pytest.mark.parametrize(
    ("kwargs", "exception", "match"),
    [
        ({"is_nullable": True}, TypeError, r"Unknown anyschema metadata key\(s\): 'is_nullable'"),
        ({"foo": 1, "bar": 2}, TypeError, "'bar', 'foo'.*pass other metadata via `custom=`"),
        ({"custom": [("foo", "bar")]}, TypeError, "Expected `custom` to be a mapping"),
        ({"custom": {"anyschema": {"unique": True}}}, TypeError, r"reserved key\(s\) 'anyschema'"),
        ({"custom": {"x-anyschema": {"dtype": "Int8"}, "pii": 1}}, TypeError, r"reserved key\(s\) 'x-anyschema'"),
        ({"dtype": 42}, TypeError, "Expected `dtype` value to be of type"),
        ({"dtype": nw.Int32}, TypeError, "Expected `dtype` value to be of type"),
        ({"dtype": None}, TypeError, "Expected `dtype` value to be of type"),
        ({"dtype": "NotADType"}, UnsupportedDTypeError, "Unable to deserialize 'NotADType'"),
    ],
)
def test_with_anyschema_invalid_raises(kwargs: dict[str, Any], exception: type[Exception], match: str) -> None:
    with pytest.raises(exception, match=match):
        WithAnySchema(**kwargs)


def test_with_anyschema_is_frozen() -> None:
    with pytest.raises(FrozenInstanceError):
        WithAnySchema(dtype="Int32").anyschema = {}  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        WithAnySchema().custom = {}  # type: ignore[misc]


def test_with_anyschema_hashable_and_equal() -> None:
    # Unhashable values must not break hashing: Python 3.10 hashes `Union` args.
    marker = WithAnySchema(unique=True, custom={"foo": [1, 2]})
    assert hash(marker) == hash(WithAnySchema(unique=True, custom={"foo": [1, 2]}))
    assert marker == WithAnySchema(unique=True, custom={"foo": [1, 2]})
    assert marker != WithAnySchema(custom={"foo": [1, 2]})
    assert Optional[Annotated[int, marker]] == Annotated[int, marker] | None  # pyright: ignore[reportOperatorIssue]


A = WithAnySchema(description="a")
B = WithAnySchema(custom={"foo": "b"})
D = WithAnySchema(dtype="Int32")


@pytest.mark.parametrize(
    ("tp", "expected_type", "expected_markers", "expected_nullable"),
    [
        (int, int, (), False),
        (Optional[int], Optional[int], (), True),
        (Annotated[int, Gt(0)], Annotated[int, Gt(0)], (), False),
        (Annotated[int, A], int, (A,), False),
        (Annotated[int, A, B, D], int, (A, B, D), False),
        (Annotated[int, Gt(0), A], Annotated[int, Gt(0)], (A,), False),
        (Annotated[int, A] | None, Optional[int], (A,), True),  # pyright: ignore[reportOperatorIssue]
        (Optional[Annotated[int, Gt(0), A]], Optional[Annotated[int, Gt(0)]], (A,), True),
        (Annotated[int | None, A], Optional[int], (A,), True),
        (Annotated[Annotated[int, A] | None, B], Optional[int], (A, B), True),
        (Annotated[Annotated[int, D, A], B], int, (D, A, B), False),
        # `Annotated` layers after the `| None` are field level; a second `| None` layer is not.
        (Annotated[Annotated[Annotated[int, A] | None, B] | None, D], Optional[Annotated[int, A]], (B, D), True),
        # Nested markers are untouched
        (list[Annotated[int, A]], list[Annotated[int, A]], (), False),
        (Annotated[list[Annotated[int, D]], A], list[Annotated[int, D]], (A,), False),
        # Unsupported unions are untouched (UnionTypeStep raises later)
        (Union[Annotated[int, A], str], Union[Annotated[int, A], str], (), False),
    ],
)
def test_split_field_markers(
    tp: Any, expected_type: Any, expected_markers: tuple[Any, ...], *, expected_nullable: bool
) -> None:
    result_type, markers = split_field_markers(tp)
    assert result_type == expected_type
    assert markers == expected_markers
    assert field_contains_none(result_type) is expected_nullable


def test_split_field_markers_returns_input_unchanged_without_markers() -> None:
    tp = int | None
    assert split_field_markers(tp)[0] is tp
