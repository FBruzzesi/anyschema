from __future__ import annotations

from typing import TYPE_CHECKING, ForwardRef

from anyschema.parsers._base import TypeParser

if TYPE_CHECKING:
    from narwhals.dtypes import DType


class ForwardRefParser(TypeParser):
    """Parser for ForwardRef types (string annotations and forward references).

    This parser handles type annotations that are forward references (ForwardRef),
    which occur when using string annotations or referencing types before they're defined.

    The parser resolves the ForwardRef to the actual type and delegates to the parser chain.
    """

    def __init__(self, globalns: dict | None = None, localns: dict | None = None) -> None:
        """Initialize the parser with namespace context for resolving forward references.

        Arguments:
            globalns: Global namespace for evaluating forward references.
                     Defaults to a namespace with common types.
            localns: Local namespace for evaluating forward references.
                    Defaults to an empty namespace.
        """
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
            "Optional": __import__("typing").Optional,
            "Union": __import__("typing").Union,
            "List": __import__("typing").List,
            "Dict": __import__("typing").Dict,
            "Tuple": __import__("typing").Tuple,
            "Set": __import__("typing").Set,
            "Annotated": __import__("typing").Annotated,
        }

        # Add user-provided globals (can override defaults)
        if user_globals:
            namespace.update(user_globals)

        return namespace

    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
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
            resolved_type = self._resolve_forward_ref(input_type)
        except (NameError, AttributeError, TypeError) as e:
            # If resolution fails, we can't handle this type
            # Log the error or re-raise depending on strictness
            msg = f"Failed to resolve ForwardRef '{input_type.__forward_arg__}': {e}"
            raise NotImplementedError(msg) from e

        return self.parser_chain.parse(resolved_type, metadata, strict=True)

    def _resolve_forward_ref(self, forward_ref: ForwardRef) -> type:
        """Resolve a ForwardRef to its actual type.

        Arguments:
            forward_ref: The ForwardRef to resolve.

        Returns:
            The resolved type.

        Raises:
            NameError: If the type name cannot be found in the namespace.
            TypeError: If the ForwardRef cannot be evaluated.
        """
        # Try using Python 3.9+ _evaluate method
        try:
            # Python 3.11+ signature
            return forward_ref._evaluate(  # type: ignore[return-value]  # noqa: SLF001
                self.globalns,
                self.localns,
                recursive_guard=frozenset(),
            )
        except TypeError:
            # Python 3.9-3.10 signature (no recursive_guard)
            try:
                return forward_ref._evaluate(  # type: ignore[call-arg,return-value]  # noqa: SLF001
                    self.globalns,
                    self.localns,
                    frozenset(),  # type: ignore[arg-type]
                )
            except TypeError:
                # Fallback: try to evaluate the string directly
                return self._evaluate_string(forward_ref.__forward_arg__)

    def _evaluate_string(self, type_string: str) -> type:
        """Evaluate a type string to get the actual type.

        Arguments:
            type_string: String representation of the type (e.g., 'int', 'list[int]').

        Returns:
            The evaluated type.

        Raises:
            NameError: If the type cannot be found.
        """
        namespace = {**self.globalns, **self.localns}
        return eval(type_string, namespace)  # type: ignore[no-any-return]  # noqa: S307


__all__ = ("ForwardRefParser",)
