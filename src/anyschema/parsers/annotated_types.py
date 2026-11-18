from __future__ import annotations

from typing import TYPE_CHECKING, Any

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

    def _parse_integer_constraints(self, constraints: FieldConstraints) -> DType:  # noqa: C901
        """Parse integer type constraints to determine the most appropriate integer dtype.

        This function examines annotated_types constraints (Gt, Ge, Lt, Le, Interval) to determine
        the smallest integer dtype that can accommodate the specified range.

        Arguments:
            constraints: Tuple of constraint objects, potentially containing annotated_types constraints.

        Returns:
            The most appropriate integer DType based on the constraints.
        """
        # Extract constraint values safely
        lower_bound, upper_bound = INT64_MIN, UINT64_MAX

        for constraint in constraints:
            if isinstance(constraint, Interval):
                # Handle Interval constraint (e.g., from pydantic conint)
                if constraint.gt is not None:
                    lower_bound = max(lower_bound, int(self._extract_numeric_value(constraint.gt)) + 1)
                if constraint.ge is not None:
                    lower_bound = max(lower_bound, int(self._extract_numeric_value(constraint.ge)))
                if constraint.lt is not None:
                    upper_bound = min(upper_bound, int(self._extract_numeric_value(constraint.lt)) - 1)
                if constraint.le is not None:
                    upper_bound = min(upper_bound, int(self._extract_numeric_value(constraint.le)))

            elif isinstance(constraint, Gt):  #  It includes pydantic PositiveInt
                lower_bound = max(lower_bound, int(self._extract_numeric_value(constraint.gt)) + 1)

            elif isinstance(constraint, Ge):  #  It includes pydantic NonNegativeInt
                lower_bound = max(lower_bound, int(self._extract_numeric_value(constraint.ge)))

            elif isinstance(constraint, Lt):
                upper_bound = min(upper_bound, int(self._extract_numeric_value(constraint.lt)) - 1)

            elif isinstance(constraint, Le):
                upper_bound = min(upper_bound, int(self._extract_numeric_value(constraint.le)))

        return int_dtype_from_bounds(lower_bound, upper_bound)

    @staticmethod
    def _extract_numeric_value(value: Any) -> int | float:
        """Safely extract a numeric value from a constraint value.

        This handles the Protocol types used by annotated_types (SupportsGt, SupportsGe, etc.)
        by converting them to int or float.

        Arguments:
            value: The value to extract, which may be a number or a Protocol type.

        Returns:
            The numeric value as int or float.

        Raises:
            TypeError: If the value cannot be converted to a number.
        """
        if value is None:
            msg = "Cannot extract numeric value from None"
            raise TypeError(msg)

        if isinstance(value, (int, float)):
            return value

        try:
            return int(value)
        except (TypeError, ValueError):
            try:
                return float(value)
            except (TypeError, ValueError) as e:
                msg = f"Cannot convert {type(value).__name__} to numeric value: {value}"
                raise TypeError(msg) from e
