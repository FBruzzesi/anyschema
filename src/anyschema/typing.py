from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeAlias

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from anyschema.parsers import TypeParser

    IntoOrderedDict: TypeAlias = Mapping[str, type] | Sequence[tuple[str, type]]
    IntoParserChain: TypeAlias = Literal["auto"] | Sequence[TypeParser]
    ModelType: TypeAlias = Literal["pydantic", "python"] | None
