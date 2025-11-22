from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal, overload

from anyschema._utils import qualified_type_name
from anyschema.exceptions import UnavailableParseChainError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from narwhals.dtypes import DType

__all__ = ("ParserChain", "TypeParser")


class TypeParser(ABC):
    """Abstract base class for type parsers that convert type annotations to Narwhals dtypes.

    This class provides a framework for parsing different types of type annotations
    and converting them into appropriate Narwhals data types. Each concrete parser
    implementation handles specific type patterns or annotation styles.

    Attributes:
        _parser_chain: Internal reference to the parser chain this parser belongs to.
        parser_chain: Property to access the parser chain, raises UnavailableParseChainError
            if not set.

    Raises:
        UnavailableParseChainError: When accessing parser_chain before it's been set.
        TypeError: When setting parser_chain with an object that's not a ParserChain instance.

    Note:
        Subclasses must implement the `parse` method to define their specific parsing logic.
    """

    _parser_chain: ParserChain | None = None

    @property
    def parser_chain(self) -> ParserChain:
        """Property that returns the parser chain instance.

        Returns:
            ParserChain: The parser chain object used for parsing operations.

        Raises:
            UnavailableParseChainError: If the parser chain has not been initialized
                (i.e., `_parser_chain` is None).
        """
        if self._parser_chain is None:
            msg = "`parser_chain` is not set yet. You can set it by `parser.parser_chain = chain"
            raise UnavailableParseChainError(msg)

        return self._parser_chain

    @parser_chain.setter
    def parser_chain(self, parser_chain: ParserChain) -> None:
        """Set the parser chain for this parser.

        Arguments:
            parser_chain: The parser chain to set. Must be an instance of ParserChain.

        Raises:
            TypeError: If parser_chain is not an instance of ParserChain.
        """
        if not isinstance(parser_chain, ParserChain):
            msg = f"Expected `ParserChain` object, found {type(parser_chain)}"
            raise TypeError(msg)

        self._parser_chain = parser_chain

    @abstractmethod
    def parse(self, input_type: type, metadata: tuple = ()) -> DType | None:
        """Parse a type annotation into a Narwhals dtype.

        Arguments:
            input_type: The type to parse (e.g., int, str, list[int], etc.)
            metadata: Optional metadata associated with the type (e.g., constraints)

        Returns:
            A Narwhals DType if the parser can handle this type, None otherwise.
        """
        ...


class ParserChain:
    """A chain of type parsers that tries each parser in sequence.

    This allows for composable parsing where multiple parsers can be tried
    until one successfully handles the type.
    """

    def __init__(self, parsers: Sequence[TypeParser]) -> None:
        """Initialize the parser chain with a list of parsers.

        Arguments:
            parsers: List of parser instances to try in order.
        """
        self.parsers = tuple(parsers)

    @overload
    def parse(self, input_type: type, metadata: tuple = (), *, strict: Literal[True] = True) -> DType: ...
    @overload
    def parse(self, input_type: type, metadata: tuple = (), *, strict: Literal[False]) -> DType | None: ...

    def parse(self, input_type: type, metadata: tuple = (), *, strict: bool = True) -> DType | None:
        """Try each parser in sequence until one succeeds.

        Arguments:
            input_type: The type to parse.
            metadata: Optional metadata associated with the type.
            strict: Whether or not to raise if unable to parse `input_type`.

        Returns:
            A Narwhals DType from the first successful parser, or None if no parser succeeded and `strict=False`.
        """
        for parser in self.parsers:
            result = parser.parse(input_type, metadata)
            if result is not None:
                return result

        if strict:
            msg = (
                f"No parser in chain could handle type: {qualified_type_name(input_type)}.\n"
                f"Please consider reporting a feature request https://github.com/FBruzzesi/anyschema/issues"
            )
            raise NotImplementedError(msg)
        return None
