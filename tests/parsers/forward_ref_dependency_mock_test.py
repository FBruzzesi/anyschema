from __future__ import annotations

from typing import ForwardRef
from unittest.mock import patch

import narwhals as nw
import pytest

from anyschema.parsers import ForwardRefStep, ParserPipeline


def test_pydantic_names_do_not_resolve_without_pydantic() -> None:
    # pydantic is imported in this process, so only the availability flag keeps its names out.
    with patch(target="anyschema.parsers._forward_ref.PYDANTIC_AVAILABLE", new=False):
        pipeline = ParserPipeline("auto")

        with pytest.raises(NotImplementedError, match="PositiveInt"):
            pipeline.parse(ForwardRef("PositiveInt"), (), {})
        assert pipeline.parse(ForwardRef("List[int]"), (), {}) == nw.List(nw.Int64())


def test_build_namespace_without_annotated_types() -> None:
    """Test that annotated_types are excluded when ANNOTATED_TYPES_AVAILABLE is False."""
    with patch(target="anyschema.parsers._forward_ref.ANNOTATED_TYPES_AVAILABLE", new=False):
        step = ForwardRefStep()

        # annotated_types should NOT be in the namespace
        assert "Gt" not in step.globalns
        assert "Ge" not in step.globalns
        assert "Lt" not in step.globalns
        assert "Le" not in step.globalns
        assert "Interval" not in step.globalns

        # But builtin types should still be there
        assert "int" in step.globalns
        assert "str" in step.globalns


def test_build_namespace_without_both_optional_deps() -> None:
    """Test namespace with neither pydantic nor annotated_types."""
    with (
        patch(target="anyschema.parsers._forward_ref.PYDANTIC_AVAILABLE", new=False),
        patch(target="anyschema.parsers._forward_ref.ANNOTATED_TYPES_AVAILABLE", new=False),
    ):
        step = ForwardRefStep()

        # No annotated_types
        assert "Gt" not in step.globalns
        assert "Interval" not in step.globalns

        # But builtin types should still be there
        assert "int" in step.globalns
        assert "str" in step.globalns
        assert "list" in step.globalns
        assert "dict" in step.globalns
        assert "Union" in step.globalns


def test_build_namespace_with_user_globals_override() -> None:
    """Test that user-provided globals can override defaults."""
    with (
        patch(target="anyschema.parsers._forward_ref.PYDANTIC_AVAILABLE", new=False),
        patch(target="anyschema.parsers._forward_ref.ANNOTATED_TYPES_AVAILABLE", new=False),
    ):
        # User provides their own types
        custom_globals = {"CustomType": int, "int": str}  # Intentionally override int
        step = ForwardRefStep(globalns=custom_globals)

        # User's custom type should be present
        assert "CustomType" in step.globalns
        assert step.globalns["CustomType"] is int

        # User's override should work (though not recommended!)
        assert step.globalns["int"] is str

        # Built-in types that weren't overridden should still be there
        assert "str" in step.globalns
        assert "list" in step.globalns
