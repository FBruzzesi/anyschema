from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeVar, get_args, overload

from narwhals.dtypes import DType

from anyschema._utils import qualified_type_name
from anyschema.serde import deserialize_dtype
from anyschema.typing import AnySchemaMetadataKey, AnySchemaNamespaceKey

if TYPE_CHECKING:
    from collections.abc import Iterable

    from narwhals.typing import TimeUnit
    from typing_extensions import Unpack

    from anyschema.typing import AnySchemaMetadata, FieldMetadata


def _get_anyschema_metadata(metadata: FieldMetadata) -> AnySchemaMetadata:
    """Get the nested anyschema metadata dictionary from field metadata.

    Supports both "anyschema" and "x-anyschema" keys (OpenAPI convention).
    Returns empty dict if neither key exists or if the value is not a dictionary.

    Arguments:
        metadata: The field metadata dictionary.

    Returns:
        The anyschema metadata dictionary, or empty dict if not found.

    Notes:
        This function tries "x-anyschema" (OpenAPI convention) first, then "anyschema".
    """
    for key in ("x-anyschema", "anyschema"):
        if anyschema_meta := metadata.get(key):
            return anyschema_meta  # type: ignore[no-any-return]
    return {}


@overload
def get_anyschema_value_by_key(
    metadata: FieldMetadata, *, key: Literal["nullable", "unique"], default: bool
) -> bool: ...


@overload
def get_anyschema_value_by_key(
    metadata: FieldMetadata, *, key: Literal["time_unit"], default: Literal["us"]
) -> TimeUnit: ...


@overload
def get_anyschema_value_by_key(
    metadata: FieldMetadata, *, key: Literal["nullable", "unique"], default: None = None
) -> bool | None: ...


@overload
def get_anyschema_value_by_key(
    metadata: FieldMetadata, *, key: Literal["time_unit"], default: Literal["us"] | None
) -> TimeUnit | None: ...


@overload
def get_anyschema_value_by_key(
    metadata: FieldMetadata, *, key: Literal["description", "time_zone"], default: str | None = None
) -> str | None: ...


@overload
def get_anyschema_value_by_key(metadata: FieldMetadata, *, key: Literal["precision", "scale"], default: int) -> int: ...


@overload
def get_anyschema_value_by_key(
    metadata: FieldMetadata, *, key: Literal["precision", "scale"], default: int | None = None
) -> int | None: ...


@overload
def get_anyschema_value_by_key(
    metadata: FieldMetadata, *, key: Literal["dtype"], default: None = None
) -> DType | str | None: ...


def get_anyschema_value_by_key(
    metadata: FieldMetadata,
    *,
    key: AnySchemaMetadataKey,
    default: bool | str | int | None = None,
) -> bool | str | int | DType | TimeUnit | None:
    """Get a specific anyschema metadata value with fallback to default.

    Supports both "anyschema" and "x-anyschema" keys (OpenAPI convention).

    Arguments:
        metadata: The field metadata dictionary.
        key: The anyschema metadata key to retrieve.
        default: Default value to return if key is not found.

    Returns:
        The metadata value, or default if not found.

    Examples:
        >>> metadata = {"anyschema": {"nullable": True, "unique": False}}
        >>> get_anyschema_value_by_key(metadata, key="nullable")
        True
        >>> get_anyschema_value_by_key(metadata, key="time_zone", default="UTC")
        'UTC'
        >>> metadata_openapi = {"x-anyschema": {"nullable": True}}
        >>> get_anyschema_value_by_key(metadata_openapi, key="nullable")
        True
    """
    return _get_anyschema_metadata(metadata).get(key, default)  # pyrefly: ignore[bad-return]


@overload
def set_anyschema_meta(metadata: FieldMetadata, *, key: Literal["nullable", "unique"], value: bool) -> None: ...


@overload
def set_anyschema_meta(
    metadata: FieldMetadata, *, key: Literal["description", "time_zone"], value: str | None
) -> None: ...


@overload
def set_anyschema_meta(metadata: FieldMetadata, *, key: Literal["precision", "scale"], value: int | None) -> None: ...


@overload
def set_anyschema_meta(metadata: FieldMetadata, *, key: Literal["time_unit"], value: TimeUnit) -> None: ...


def set_anyschema_meta(
    metadata: FieldMetadata, *, key: AnySchemaMetadataKey, value: bool | str | int | TimeUnit | None
) -> None:
    """Set a specific anyschema metadata value in the nested structure.

    Writes to `metadata` in place. The nested namespace dict is replaced by an updated copy instead of being
    edited, because the user's spec may share it (e.g. a Pydantic `json_schema_extra`).

    Arguments:
        metadata: The field metadata dictionary to modify.
        key: The anyschema metadata key to set.
        value: The value to set.

    Examples:
        >>> metadata: dict = {}
        >>> set_anyschema_meta(metadata, key="nullable", value=True)
        >>> metadata
        {'anyschema': {'nullable': True}}
        >>> set_anyschema_meta(metadata, key="unique", value=False)
        >>> metadata
        {'anyschema': {'nullable': True, 'unique': False}}

    Notes:
        If "x-anyschema" already exists in the metadata, it will be used;
        otherwise "anyschema" is used (the default). This preserves the user's
        choice of namespace key.
    """
    namespace_key: AnySchemaNamespaceKey = "x-anyschema" if "x-anyschema" in metadata else "anyschema"
    metadata[namespace_key] = {**metadata.get(namespace_key, {}), key: value}


def filter_anyschema_metadata(metadata: Mapping[str, Any]) -> FieldMetadata:
    """Filter out anyschema-specific metadata keys, returning only custom metadata.

    Removes both "anyschema" and "x-anyschema" keys to support both conventions.

    Arguments:
        metadata: The field metadata dictionary.

    Returns:
        A new dictionary with anyschema keys removed.

    Examples:
        >>> metadata = {"anyschema": {"nullable": True}, "custom": "value", "x-anyschema": {"unique": False}}
        >>> filter_anyschema_metadata(metadata)
        {'custom': 'value'}
    """
    return {key: value for key, value in metadata.items() if key not in {"anyschema", "x-anyschema"}}


_T = TypeVar("_T")

_NAMESPACE_KEYS: frozenset[AnySchemaNamespaceKey] = frozenset(get_args(AnySchemaNamespaceKey))
_METADATA_KEYS: frozenset[AnySchemaMetadataKey] = frozenset(get_args(AnySchemaMetadataKey))


def ensure_dtype(into_dtype: object) -> DType:
    """Return `into_dtype` as a Narwhals `DType`, deserializing it first if it is a string.

    Raises:
        TypeError: If `into_dtype` is neither a `DType` instance nor a `str`.
        UnsupportedDTypeError: If `into_dtype` is a string that cannot be deserialized.
    """
    if isinstance(into_dtype, DType):
        return into_dtype
    if isinstance(into_dtype, str):
        return deserialize_dtype(into_dtype)
    msg = (
        "Expected `dtype` value to be of type `narwhals.dtypes.DType` or `str`, "
        f"found '{qualified_type_name(into_dtype)}' instead."
    )
    raise TypeError(msg)


@dataclass(frozen=True, init=False, repr=False)
class WithAnySchema:
    """`Annotated` marker that sets the anyschema dtype and metadata of a field, for any spec.

    Keyword arguments are the anyschema metadata keys (`dtype`, `nullable`, `unique`, `description`, `time_zone`,
    ...). Any other metadata goes in `custom` and ends up in [`AnyField.metadata`][anyschema.AnyField]. A `dtype`
    skips type parsing for that field.

    Nested markers (e.g. inside `list[...]`) can only set `dtype`. Every other key is only valid at the field level:
    in the `Annotated` layers of a field type, optionally wrapped in a single `| None`.

    Arguments:
        custom: Custom metadata, copied on construction.
        **anyschema: Anyschema metadata keys. A `dtype` string is deserialized on construction (see
            [`deserialize_dtype`][anyschema.serde.deserialize_dtype]).

    Raises:
        TypeError: On an unknown keyword argument, if `custom` is not a mapping or contains an `"anyschema"` /
            `"x-anyschema"` key, or if `dtype` is neither a `DType` instance nor a `str`.
        UnsupportedDTypeError: If `dtype` is a string that cannot be deserialized.

    Examples:
        >>> from typing import Annotated
        >>> from anyschema import AnySchema, WithAnySchema
        >>>
        >>> WithAnySchema(dtype="Int32", unique=True, custom={"pii": True})
        WithAnySchema(dtype=Int32, unique=True, custom={'pii': True})
        >>> Email = Annotated[str, WithAnySchema(unique=True, custom={"pii": True})]
        >>> schema = AnySchema(
        ...     spec={
        ...         "id": Annotated[int, WithAnySchema(dtype="Int32")],
        ...         "email": Annotated[Email, WithAnySchema(description="Primary email")],
        ...         "tags": list[Annotated[str, WithAnySchema(dtype="Categorical")]],
        ...     }
        ... )
        >>> {name: field.dtype for name, field in schema.fields.items()}
        {'id': Int32, 'email': String, 'tags': List(Categorical)}
        >>> schema.fields["email"]
        AnyField(name='email', dtype=String, nullable=False, unique=True, description='Primary email', metadata={'pii': True})
    """  # noqa: E501

    anyschema: AnySchemaMetadata
    custom: Mapping[str, Any]

    def __init__(self, *, custom: Mapping[str, Any] | None = None, **anyschema: Unpack[AnySchemaMetadata]) -> None:
        if unknown := sorted(anyschema.keys() - _METADATA_KEYS):
            msg = (
                f"Unknown anyschema metadata key(s): {', '.join(map(repr, unknown))}. "
                f"Expected any of {', '.join(map(repr, sorted(_METADATA_KEYS)))}; pass other metadata via `custom=`."
            )
            raise TypeError(msg)
        custom = {} if custom is None else custom
        if not isinstance(custom, Mapping):  # pyright: ignore[reportUnnecessaryIsInstance]
            msg = f"Expected `custom` to be a mapping, found '{qualified_type_name(custom)}' instead."
            raise TypeError(msg)
        if reserved := sorted(custom.keys() & _NAMESPACE_KEYS):
            msg = (
                f"`custom` cannot contain the reserved key(s) {', '.join(map(repr, reserved))}: pass anyschema "
                "metadata as keyword arguments instead, e.g. `WithAnySchema(unique=True)`."
            )
            raise TypeError(msg)
        if "dtype" in anyschema:
            anyschema["dtype"] = ensure_dtype(anyschema["dtype"])
        object.__setattr__(self, "anyschema", anyschema)  # `**anyschema` is already a fresh dict
        object.__setattr__(self, "custom", dict(custom))

    @property
    def dtype(self) -> DType | None:
        """The Narwhals dtype set by the marker, if any."""
        dtype = self.anyschema.get("dtype")
        return dtype if isinstance(dtype, DType) else None

    def __hash__(self) -> int:
        # Python 3.10 hashes `Union` args and values may be unhashable (e.g. `dict`): hash the keys only.
        return hash((frozenset(self.anyschema), frozenset(self.custom)))

    def __repr__(self) -> str:
        args = [f"{key}={value!r}" for key, value in self.anyschema.items()]
        if self.custom:
            args.append(f"custom={self.custom!r}")
        return f"{type(self).__name__}({', '.join(args)})"


def partition_markers(extras: Iterable[_T]) -> tuple[tuple[WithAnySchema, ...], tuple[_T, ...]]:
    """Split `Annotated` extras into `(markers, everything else)`, keeping their order."""
    markers: list[WithAnySchema] = []
    others: list[_T] = []
    for extra in extras:
        if isinstance(extra, WithAnySchema):
            markers.append(extra)
        else:
            others.append(extra)
    return tuple(markers), tuple(others)


def merge_field_markers(field_name: str, metadata: FieldMetadata, markers: Iterable[WithAnySchema]) -> FieldMetadata:
    """Merge field-level markers into a copy of the spec's own field metadata.

    The last marker wins per key: anyschema keys one by one, `custom` keys shallow-merged.

    Arguments:
        field_name: The field name, used in error messages.
        metadata: The spec's own field metadata, with at most one of the `"anyschema"` / `"x-anyschema"` keys.
        markers: The field-level markers, innermost first.

    Raises:
        ValueError: If a key is set both by a marker and by the spec's own metadata, even with equal values.
    """
    marker_anyschema: AnySchemaMetadata = {}
    marker_custom: dict[str, Any] = {}
    for marker in markers:
        marker_anyschema.update(marker.anyschema)
        marker_custom.update(marker.custom)

    spec_anyschema = _get_anyschema_metadata(metadata)
    conflicts = [
        *sorted(marker_anyschema.keys() & spec_anyschema.keys()),
        *sorted(marker_custom.keys() & metadata.keys()),
    ]
    if conflicts:
        keys = ", ".join(f"'{key}'" for key in conflicts)
        msg = (
            f"Conflicting metadata for field '{field_name}': the following key(s) are set both by `Annotated` markers "
            f"(`WithAnySchema`) and by the spec's own field metadata: {keys}."
        )
        raise ValueError(msg)

    namespace_key: AnySchemaNamespaceKey = "x-anyschema" if "x-anyschema" in metadata else "anyschema"
    return {**metadata, **marker_custom, namespace_key: {**(metadata.get(namespace_key) or {}), **marker_anyschema}}
