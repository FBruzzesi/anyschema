from __future__ import annotations

from typing import TYPE_CHECKING

import narwhals as nw

if TYPE_CHECKING:
    from narwhals.dtypes import DType


def parse_datetime_metadata(metadata: list) -> DType:
    match metadata:
        case _:
            return nw.Datetime()
