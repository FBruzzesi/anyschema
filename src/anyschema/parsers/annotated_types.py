from __future__ import annotations

import math
from typing import TYPE_CHECKING

from annotated_types import Ge, Gt, Interval, Le, Lt

from anyschema._utils import INT64_MIN, UINT64_MAX, int_dtype_from_bounds
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType

    from anyschema.typing import FieldConstraints, FieldMetadata, FieldType


__all__ = ("AnnotatedTypesStep",)


class AnnotatedTypesStep(ParserStep):
    """Parser for types with `annotated_types` metadata.

    Handles:

    - Integer constraints (`Gt`, `Ge`, `Lt`, `Le`, `Interval`)
    - Type refinement based on metadata

    Warning:
        It requires [annotated-types](https://github.com/annotated-types/annotated-types) to be installed.
    """

    def parse(
        self,
        input_type: FieldType,
        constraints: FieldConstraints,
        metadata: FieldMetadata,  # noqa: ARG002
    ) -> DType | None:
        """Parse types with annotated constraints into refined Narwhals dtypes.

        Arguments:
            input_type: The type to parse.
            constraints: Constraints associated with the type (e.g., Gt, Ge, Lt, Le).
            metadata: Custom metadata dictionary (not used in this parser).

        Returns:
            A Narwhals DType if this parser can refine the type based on constraints, None otherwise.
        """
        if not constraints:
            return None

        # Check if it's a type/class and if it's int or a subclass of int (but not bool)
        # Note: bool is a subclass of int, but we don't want to apply integer constraints to booleans
        if isinstance(input_type, type) and issubclass(input_type, int) and not issubclass(input_type, bool):
            return self._parse_integer_constraints(constraints)

        # For other types, we don't refine based on constraints
        return None

    def _parse_integer_constraints(self, constraints: FieldConstraints) -> DType:
        """Parse integer type constraints to determine the most appropriate integer dtype.

        This function examines annotated_types constraints (Gt, Ge, Lt, Le, Interval) to determine
        the smallest integer dtype that can accommodate the specified range.

        Arguments:
            constraints: Tuple of constraint objects, potentially containing annotated_types constraints.

        Returns:
            The most appropriate integer DType based on the constraints.
        """
        lower_bound, upper_bound = INT64_MIN, UINT64_MAX

        # Iterating an `Interval` yields its `Gt`/`Ge`/`Lt`/`Le` parts.
        flat_constraints = (item for c in constraints for item in (c if isinstance(c, Interval) else (c,)))
        # floor/ceil, not `int()`: `Gt(-1.5)` allows -1, but `int(-1.5) + 1` is 0.
        for constraint in flat_constraints:
            if isinstance(constraint, Gt):  #  It includes pydantic PositiveInt
                lower_bound = max(lower_bound, math.floor(constraint.gt) + 1)  # type: ignore[call-overload]
            elif isinstance(constraint, Ge):  #  It includes pydantic NonNegativeInt
                lower_bound = max(lower_bound, math.ceil(constraint.ge))  # type: ignore[call-overload]
            elif isinstance(constraint, Lt):
                upper_bound = min(upper_bound, math.ceil(constraint.lt) - 1)  # type: ignore[call-overload]
            elif isinstance(constraint, Le):
                upper_bound = min(upper_bound, math.floor(constraint.le))  # type: ignore[call-overload]

        return int_dtype_from_bounds(lower_bound, upper_bound)
