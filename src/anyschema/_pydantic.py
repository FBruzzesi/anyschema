from __future__ import annotations

from datetime import date, datetime
from types import UnionType
from typing import TYPE_CHECKING, Any, GenericAlias, Union, _GenericAlias, get_args, get_origin

import narwhals as nw
from narwhals.schema import Schema
from pydantic import AwareDatetime, BaseModel, FutureDate, FutureDatetime, NaiveDatetime, PastDate, PastDatetime
from pydantic.fields import FieldInfo

from anyschema._parsers import parse_integer_constraints
from anyschema._utils import parse_union
from anyschema.exceptions import UnsupportedDTypeError

if TYPE_CHECKING:
    from narwhals.dtypes import DType


def model_to_nw_schema(model: BaseModel | type[BaseModel]) -> Schema:
    """Converts Pydantic model to Narwhals Schema."""
    return Schema(
        {field_name: pydantic_field_to_nw_type(field_info) for field_name, field_info in model.model_fields.items()}
    )


def pydantic_field_to_nw_type(field_info: FieldInfo) -> DType:  # noqa: C901, PLR0911, PLR0912
    annotation = field_info.annotation

    if isinstance(annotation, _GenericAlias | GenericAlias):
        _origin = get_origin(annotation)
        _args = get_args(annotation)

        if _origin is Union:
            _type, _metadata = parse_union(_args)
            return pydantic_field_to_nw_type(FieldInfo(annotation=_type, metadata=_metadata))

        elif _origin is list:
            # Includes:
            # - python list
            # - pydantic conlist
            _inner_metadata: tuple[Any, ...]
            _inner_type, _inner_metadata = parse_union(_args) if _args is Union else _args[0], ()
            return nw.List(inner=pydantic_field_to_nw_type(FieldInfo(annotation=_inner_type, metadata=_inner_metadata)))

        else:  # pragma: no cover
            msg = "Please report an issue at https://github.com/FBruzzesi/anyschema/issues"
            raise NotImplementedError

    elif isinstance(annotation, UnionType):
        _type, _metadata = parse_union(get_args(annotation))
        return pydantic_field_to_nw_type(FieldInfo(annotation=_type, metadata=_metadata))

    elif (isinstance(annotation, type) and issubclass(annotation, BaseModel)) or isinstance(annotation, BaseModel):
        # Includes:
        # - pydantic models
        return nw.Struct(
            [
                nw.Field(name=_inner_field_name, dtype=pydantic_field_to_nw_type(_inner_field_info))
                for _inner_field_name, _inner_field_info in annotation.model_fields.items()
            ]
        )

    else:
        _type = annotation
        _metadata = tuple(field_info.metadata)

    if _type is AwareDatetime:
        # Pydantic AwareDatetime does not fix a single timezone, but any timezone would work.
        # This cannot be used in nw.Datetime, therefore we raise an exception
        # See https://github.com/pydantic/pydantic/issues/5829
        msg = "pydantic AwareDatetime does not specify a fixed timezone."
        raise UnsupportedDTypeError(msg)

    if _type is int:
        # Includes:
        # - python int
        # - pydantic conint
        # - pydantic NegativeInt, NonNegativeInt, NonPositiveInt, PositiveInt
        return parse_integer_constraints(_metadata)

    if _type is float:
        # Includes:
        # - python float
        # - pydantic confloat
        # - pydantic FiniteFloat, NegativeFloat, NonNegativeFloat, NonPositiveFloat, PositiveFloat

        # There is no way of differentiating between Float32 and Float64 in pydantic,
        # therefore no matter what the metadata are, we always return Float64
        return nw.Float64()

    if _type is str:
        # Includes:
        # - python str
        # - pydantic constr, StrictStr
        # - pydantic Annotated[str, StringConstraints(...)]
        return nw.String()

    if _type is bool:
        # Includes:
        # - python bool
        # - pydantic StrictBool
        return nw.Boolean()

    if _type in {datetime, NaiveDatetime, PastDatetime, FutureDatetime}:
        # Includes:
        # - python datetime
        # - pydantic AwareDatetime, NaiveDatetime, PastDatetime, FutureDatetime

        # PastDatetime and FutureDatetime accept both aware and naive datetimes, here we
        # simply return nw.Datetime without timezone info.
        # This means that we won't be able to convert it to a timezone aware data type.
        return nw.Datetime()

    if _type in {date, PastDate, FutureDate}:
        # Includes:
        # - python date
        # - pydantic condate
        # - pydantic PastDate, FutureDate
        return nw.Date()

    raise NotImplementedError  # pragma: no cover


__all__ = ("model_to_nw_schema", "pydantic_field_to_nw_type")
