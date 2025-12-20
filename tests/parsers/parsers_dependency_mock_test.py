from __future__ import annotations

from unittest.mock import patch

import pytest

from anyschema.parsers import ParserPipeline


@pytest.mark.parametrize(
    ("dependency_flag", "excluded_step"),
    [
        ("ANNOTATED_TYPES_AVAILABLE", "AnnotatedTypesStep"),
        ("ATTRS_AVAILABLE", "AttrsTypeStep"),
        ("PYDANTIC_AVAILABLE", "PydanticTypeStep"),
        ("SQLALCHEMY_AVAILABLE", "SQLAlchemyTypeStep"),
    ],
)
def test_auto_pipeline_without_optional_dependency(dependency_flag: str, excluded_step: str) -> None:
    """Test that optional parser steps are excluded when their dependency is unavailable."""
    with patch(target=f"anyschema.parsers._pipeline.{dependency_flag}", new=False):
        pipeline = ParserPipeline("auto")
        step_names = [str(step) for step in pipeline.steps]

        # The corresponding step should NOT be in the pipeline
        assert excluded_step not in step_names

        # Core steps should still be there
        assert "ForwardRefStep" in step_names
        assert "PyTypeStep" in step_names


def test_auto_pipeline_without_all_optional_deps() -> None:
    """Test pipeline with only core dependencies."""
    patches = (
        patch(target="anyschema.parsers._pipeline.ANNOTATED_TYPES_AVAILABLE", new=False),
        patch(target="anyschema.parsers._pipeline.ATTRS_AVAILABLE", new=False),
        patch(target="anyschema.parsers._pipeline.PYDANTIC_AVAILABLE", new=False),
        patch(target="anyschema.parsers._pipeline.SQLALCHEMY_AVAILABLE", new=False),
    )

    for p in patches:
        p.start()

    try:
        pipeline = ParserPipeline("auto")
        step_names = [str(step) for step in pipeline.steps]

        # Only core steps should be present
        assert "ForwardRefStep" in step_names
        assert "UnionTypeStep" in step_names
        assert "AnnotatedStep" in step_names
        assert "PyTypeStep" in step_names

        # Optional steps should NOT be present
        assert "AnnotatedTypesStep" not in step_names
        assert "AttrsTypeStep" not in step_names
        assert "PydanticTypeStep" not in step_names
        assert "SQLAlchemyTypeStep" not in step_names
    finally:
        for p in patches:
            p.stop()
