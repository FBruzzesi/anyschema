from __future__ import annotations

__all__ = ("UnavailableParseChainError", "UnsupportedDTypeError")


class UnavailableParseChainError(ValueError):
    """Exception raised when a parser does not have a ParserChain set."""


class UnsupportedDTypeError(ValueError):
    """Exception raised when a DType is not supported."""
