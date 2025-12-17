from __future__ import annotations

from typing import TYPE_CHECKING, Any

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from anyschema.typing import FieldMetadata

__all__ = ("AnySchemaMetadata", "extract_anyschema_metadata", "get_anyschema_metadata", "set_anyschema_metadata")


class AnySchemaMetadata(TypedDict, total=False):
    """TypedDict for anyschema-specific metadata.

    Attributes:
        description: Human-readable field description.
        nullable: Whether the field accepts null values.
        time_zone: Timezone for datetime fields.
        time_unit: Time precision for datetime fields (default: "us").
        unique: Whether all values must be unique.
    """

    description: str | None
    nullable: bool
    time_zone: str
    time_unit: str
    unique: bool


def get_anyschema_metadata(metadata: FieldMetadata, key: str, default: Any = None) -> Any:
    """Get a value from the nested anyschema metadata.

    Arguments:
        metadata: The field metadata dictionary.
        key: The key to retrieve from anyschema metadata (without the "anyschema/" prefix).
        default: The default value if key is not found.

    Returns:
        The value from anyschema metadata or default if not found.

    Examples:
        >>> metadata = {"__anyschema_metadata__": {"nullable": True, "unique": False}}
        >>> get_anyschema_metadata(metadata, "nullable")
        True
        >>> get_anyschema_metadata(metadata, "time_zone", "UTC")
        'UTC'
    """
    anyschema_data = metadata.get("__anyschema_metadata__", {})
    return anyschema_data.get(key, default)


def set_anyschema_metadata(metadata: FieldMetadata, key: str, value: Any) -> None:
    """Set a value in the nested anyschema metadata.

    This function mutates the metadata dictionary in-place.

    Arguments:
        metadata: The field metadata dictionary to modify.
        key: The key to set in anyschema metadata (without the "anyschema/" prefix).
        value: The value to set.

    Examples:
        >>> metadata: dict = {}
        >>> set_anyschema_metadata(metadata, "nullable", True)
        >>> metadata
        {'__anyschema_metadata__': {'nullable': True}}
    """
    if "__anyschema_metadata__" not in metadata:
        metadata["__anyschema_metadata__"] = {}
    metadata["__anyschema_metadata__"][key] = value


def extract_anyschema_metadata(metadata: FieldMetadata) -> tuple[AnySchemaMetadata, dict[str, Any]]:
    """Extract and separate anyschema metadata from custom metadata.

    Arguments:
        metadata: The field metadata dictionary.

    Returns:
        A tuple of (anyschema_metadata, custom_metadata).
        - anyschema_metadata: Dict containing only anyschema-specific keys
        - custom_metadata: Dict containing all other metadata keys

    Examples:
        >>> metadata = {
        ...     "__anyschema_metadata__": {"nullable": True, "unique": False},
        ...     "custom_key": "custom_value",
        ... }
        >>> anyschema_meta, custom_meta = extract_anyschema_metadata(metadata)
        >>> anyschema_meta
        {'nullable': True, 'unique': False}
        >>> custom_meta
        {'custom_key': 'custom_value'}
    """
    anyschema_meta = metadata.get("__anyschema_metadata__", {})
    custom_meta = {k: v for k, v in metadata.items() if k != "__anyschema_metadata__"}
    return anyschema_meta, custom_meta
