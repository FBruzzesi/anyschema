from __future__ import annotations

from typing import TYPE_CHECKING

from anyschema._dependencies import get_pydantic

if TYPE_CHECKING:
    from pydantic import BaseModel
    from typing_extensions import Self


class AnySchema:
    def __init__(self: Self, model: BaseModel) -> None:
        if (pydantic := get_pydantic()) is not None and isinstance(model, pydantic.BaseModel):
            self._type = "pydantic"
        else:
            raise NotImplementedError
        self._model = model

    @classmethod
    def from_pydantic(cls: type[Self], model: BaseModel) -> Self:
        return AnySchema(model=model)
