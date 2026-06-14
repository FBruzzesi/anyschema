from __future__ import annotations

__all__ = ("UnavailablePipelineError", "UnsupportedDTypeError")


class UnavailablePipelineError(ValueError):
    """Exception raised when a parser does not have a ParserPipeline set."""


class UnsupportedDTypeError(ValueError):
    """Exception raised when a DType is not supported."""
