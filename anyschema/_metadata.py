from __future__ import annotations

from typing import TYPE_CHECKING, Literal, overload

if TYPE_CHECKING:
    from narwhals.typing import TimeUnit

    from anyschema.typing import AnySchemaMetadata, AnySchemaMetadataKey, FieldMetadata


def _get_anyschema_metadata(metadata: FieldMetadata) -> AnySchemaMetadata:
    """Get the nested anyschema metadata dictionary from field metadata.

    Supports both "anyschema" and "x-anyschema" keys (OpenAPI convention).
    Returns None if neither key exists or if the value is not a dictionary.

    Arguments:
        metadata: The field metadata dictionary.

    Returns:
        The anyschema metadata dictionary, or None if not found.
    """
    # Try "anyschema" first, then "x-anyschema" (OpenAPI convention)
    for key in ("anyschema", "x-anyschema"):
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


def get_anyschema_value_by_key(
    metadata: FieldMetadata,
    *,
    key: AnySchemaMetadataKey,
    default: bool | str | None = None,
) -> bool | str | TimeUnit | None:
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
    return _get_anyschema_metadata(metadata).get(key, default)


@overload
def set_anyschema_meta(metadata: FieldMetadata, *, key: Literal["nullable", "unique"], value: bool) -> None: ...


@overload
def set_anyschema_meta(
    metadata: FieldMetadata, *, key: Literal["description", "time_zone"], value: str | None
) -> None: ...


@overload
def set_anyschema_meta(metadata: FieldMetadata, *, key: Literal["time_unit"], value: TimeUnit) -> None: ...


def set_anyschema_meta(
    metadata: FieldMetadata, *, key: AnySchemaMetadataKey, value: bool | str | TimeUnit | None
) -> None:
    """Set a specific anyschema metadata value in the nested structure.

    Creates the nested dictionary if it doesn't exist. Modifies the metadata dict in-place.

    Arguments:
        metadata: The field metadata dictionary to modify.
        key: The anyschema metadata key to set.
        value: The value to set.
        use_x_prefix: If True, use "x-anyschema" instead of "anyschema" (OpenAPI convention).

    Examples:
        >>> metadata: dict = {}
        >>> set_anyschema_meta(metadata, key="nullable", value=True)
        >>> metadata
        {'anyschema': {'nullable': True}}
        >>> set_anyschema_meta(metadata, key="unique", value=False)
        >>> metadata
        {'anyschema': {'nullable': True, 'unique': False}}
    """
    anyschema_key = "x-anyschema" if "x-anyschema" in metadata else "anyschema"
    if anyschema_key not in metadata:
        metadata[anyschema_key] = {}

    metadata[anyschema_key][key] = value


def filter_anyschema_metadata(metadata: FieldMetadata) -> FieldMetadata:
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
    return {key: value for key, value in metadata.items() if key not in ("anyschema", "x-anyschema")}
