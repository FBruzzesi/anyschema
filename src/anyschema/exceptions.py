from __future__ import annotations


class UnsupportedDTypeError(ValueError):
    """Exception raised when a DType is not supported."""


class UnavailableParseChainError(ValueError):
    """Exception raised when a parser does not have a ParserChain set."""
