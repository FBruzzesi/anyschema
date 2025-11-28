from __future__ import annotations

from typing import TYPE_CHECKING, Any, ForwardRef

from typing_extensions import evaluate_forward_ref

from anyschema._dependencies import ANNOTATED_TYPES_AVAILABLE, PYDANTIC_AVAILABLE
from anyschema.parsers._base import ParserStep

if TYPE_CHECKING:
    from narwhals.dtypes import DType


class ForwardRefStep(ParserStep):
    """Parser for ForwardRef types (string annotations and forward references).

    This parser handles type annotations that are forward references (ForwardRef),
    which occur when using string annotations or referencing types before they're defined.

    The parser resolves the ForwardRef to the actual type and delegates to the parser chain.

    Initialization can be customized by providing a global and local namespace that will be used to evaluate the
    forward references when resolving the type. The default namespace is built with common types, yet you can override
    it with your own types.

    Arguments:
        globalns: Global namespace for evaluating forward references. Defaults to a namespace with common types.
        localns: Local namespace for evaluating forward references. Defaults to an empty namespace.
    """

    def __init__(self, globalns: dict | None = None, localns: dict | None = None) -> None:
        super().__init__()
        # Build namespace with common types for resolution
        self.globalns = self._build_namespace(globalns)
        self.localns = localns if localns is not None else {}

    def _build_namespace(self, user_globals: dict | None) -> dict:
        """Build a namespace with common types for ForwardRef resolution.

        Arguments:
            user_globals: User-provided global namespace.

        Returns:
            A namespace with built-in types and typing constructs.
        """
        namespace = {
            # Built-in types
            "int": int,
            "str": str,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            # Typing constructs
            "Annotated": __import__("typing").Annotated,
            "Dict": __import__("typing").Dict,
            "List": __import__("typing").List,
            "Optional": __import__("typing").Optional,
            "Set": __import__("typing").Set,
            "Union": __import__("typing").Union,
            "Tuple": __import__("typing").Tuple,
        }

        # Add pydantic types if available
        if PYDANTIC_AVAILABLE:
            import pydantic

            pydantic_types = {
                "BaseModel": pydantic.BaseModel,
                "Field": pydantic.Field,
                # Constrained integers
                "PositiveInt": pydantic.PositiveInt,
                "NegativeInt": pydantic.NegativeInt,
                "NonPositiveInt": pydantic.NonPositiveInt,
                "NonNegativeInt": pydantic.NonNegativeInt,
                # Constrained floats
                "PositiveFloat": pydantic.PositiveFloat,
                "NegativeFloat": pydantic.NegativeFloat,
                "NonPositiveFloat": pydantic.NonPositiveFloat,
                "NonNegativeFloat": pydantic.NonNegativeFloat,
                # constraints
                "constr": pydantic.constr,
                "conint": pydantic.conint,
                "confloat": pydantic.confloat,
                "conlist": pydantic.conlist,
                "conset": pydantic.conset,
            }
            namespace.update(pydantic_types)

        # Add annotated-types if available
        if ANNOTATED_TYPES_AVAILABLE:
            import annotated_types

            annotated_types_dict = {
                "Gt": annotated_types.Gt,
                "Ge": annotated_types.Ge,
                "Lt": annotated_types.Lt,
                "Le": annotated_types.Le,
                "Interval": annotated_types.Interval,
                "MultipleOf": annotated_types.MultipleOf,
                "MinLen": annotated_types.MinLen,
                "MaxLen": annotated_types.MaxLen,
                "Len": annotated_types.Len,
                "Timezone": annotated_types.Timezone,
                "Predicate": annotated_types.Predicate,
            }
            namespace.update(annotated_types_dict)

        # Add user-provided globals (can override defaults)
        if user_globals:
            namespace.update(user_globals)

        return namespace

    def parse(self, input_type: Any, metadata: tuple = ()) -> DType | None:
        """Parse ForwardRef types by resolving them and delegating to the chain.

        Arguments:
            input_type: The type to parse (may be a ForwardRef).
            metadata: Optional metadata associated with the type.

        Returns:
            A Narwhals DType if this is a ForwardRef that can be resolved, None otherwise.
        """
        if not isinstance(input_type, ForwardRef):
            return None

        try:
            resolved_type = evaluate_forward_ref(
                forward_ref=input_type,
                globals=self.globalns,
                locals=self.localns,
            )
        except (NameError, AttributeError, TypeError) as e:
            # If resolution fails, we can't handle this type
            msg = f"Failed to resolve ForwardRef '{input_type.__forward_arg__}': {e}"
            raise NotImplementedError(msg) from e

        return self.pipeline.parse(resolved_type, metadata, strict=True)
