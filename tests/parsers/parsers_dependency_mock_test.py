from __future__ import annotations

from unittest.mock import patch

from anyschema.parsers import make_pipeline
from anyschema.parsers._pipeline import _auto_pipeline


def test_auto_pipeline_without_annotated_types() -> None:
    """Test that AnnotatedTypesStep is excluded when ANNOTATED_TYPES_AVAILABLE is False."""
    with patch(target="anyschema.parsers._pipeline.ANNOTATED_TYPES_AVAILABLE", new=False):
        # Clear the cache to force regeneration
        _auto_pipeline.cache_clear()
        try:
            pipeline = make_pipeline("auto")
            step_names = [type(step).__name__ for step in pipeline.steps]

            # AnnotatedTypesStep should NOT be in the pipeline
            assert "AnnotatedTypesStep" not in step_names

            # But these should still be there
            assert "ForwardRefStep" in step_names
            assert "UnionTypeStep" in step_names
            assert "PyTypeStep" in step_names
        finally:
            # Clear cache again to restore normal state
            _auto_pipeline.cache_clear()


def test_auto_pipeline_without_attrs() -> None:
    """Test that AttrsTypeStep is excluded when ATTRS_AVAILABLE is False."""
    with patch(target="anyschema.parsers._pipeline.ATTRS_AVAILABLE", new=False):
        _auto_pipeline.cache_clear()
        try:
            pipeline = make_pipeline("auto")
            step_names = [type(step).__name__ for step in pipeline.steps]

            # AttrsTypeStep should NOT be in the pipeline
            assert "AttrsTypeStep" not in step_names

            # But these should still be there
            assert "ForwardRefStep" in step_names
            assert "PyTypeStep" in step_names
        finally:
            _auto_pipeline.cache_clear()


def test_auto_pipeline_without_pydantic() -> None:
    """Test that PydanticTypeStep is excluded when PYDANTIC_AVAILABLE is False."""
    with patch(target="anyschema.parsers._pipeline.PYDANTIC_AVAILABLE", new=False):
        _auto_pipeline.cache_clear()
        try:
            pipeline = make_pipeline("auto")
            step_names = [type(step).__name__ for step in pipeline.steps]

            # PydanticTypeStep should NOT be in the pipeline
            assert "PydanticTypeStep" not in step_names

            # But these should still be there
            assert "ForwardRefStep" in step_names
            assert "PyTypeStep" in step_names
        finally:
            _auto_pipeline.cache_clear()


def test_auto_pipeline_without_sqlalchemy() -> None:
    """Test that SQLAlchemyTypeStep is excluded when SQLALCHEMY_AVAILABLE is False."""
    with patch(target="anyschema.parsers._pipeline.SQLALCHEMY_AVAILABLE", new=False):
        _auto_pipeline.cache_clear()
        try:
            pipeline = make_pipeline("auto")
            step_names = [type(step).__name__ for step in pipeline.steps]

            # SQLAlchemyTypeStep should NOT be in the pipeline
            assert "SQLAlchemyTypeStep" not in step_names

            # But these should still be there
            assert "ForwardRefStep" in step_names
            assert "PyTypeStep" in step_names
        finally:
            _auto_pipeline.cache_clear()


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
        _auto_pipeline.cache_clear()
        pipeline = make_pipeline("auto")
        step_names = [type(step).__name__ for step in pipeline.steps]

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
        _auto_pipeline.cache_clear()
