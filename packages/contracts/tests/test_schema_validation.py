"""Test that example payloads validate against Pydantic models and JSON schemas."""

import json
from pathlib import Path

import pytest

from m2la_contracts.analyze import AnalyzeRequest, AnalyzeResponse
from m2la_contracts.common import ArtifactManifest
from m2la_contracts.transform import TransformRequest, TransformResponse
from m2la_contracts.validate import ValidationReport

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"

# Map example filenames to their Pydantic model class
EXAMPLE_MODEL_MAP: dict[str, type] = {
    "analyze_request_project.json": AnalyzeRequest,
    "analyze_request_single_flow.json": AnalyzeRequest,
    "analyze_response_project.json": AnalyzeResponse,
    "analyze_response_single_flow.json": AnalyzeResponse,
    "transform_request_project.json": TransformRequest,
    "transform_response_project.json": TransformResponse,
    "transform_response_single_flow.json": TransformResponse,
    "validation_report.json": ValidationReport,
}

# Map schema filenames to their Pydantic model class for schema structure validation
SCHEMA_MODEL_MAP: dict[str, type] = {
    "analyze_request.schema.json": AnalyzeRequest,
    "analyze_response.schema.json": AnalyzeResponse,
    "transform_request.schema.json": TransformRequest,
    "transform_response.schema.json": TransformResponse,
    "validation_report.schema.json": ValidationReport,
    "artifact_manifest.schema.json": ArtifactManifest,
}


class TestExamplePayloads:
    """Validate that all example payloads can be deserialized by Pydantic models."""

    @pytest.mark.parametrize(
        "filename,model_cls",
        list(EXAMPLE_MODEL_MAP.items()),
        ids=list(EXAMPLE_MODEL_MAP.keys()),
    )
    def test_example_validates_against_model(self, filename: str, model_cls: type) -> None:
        """Each example payload should successfully validate against its Pydantic model."""
        example_path = EXAMPLES_DIR / filename
        assert example_path.exists(), f"Example file not found: {example_path}"

        raw_json = example_path.read_text()
        instance = model_cls.model_validate_json(raw_json)
        assert instance is not None

    @pytest.mark.parametrize(
        "filename,model_cls",
        list(EXAMPLE_MODEL_MAP.items()),
        ids=list(EXAMPLE_MODEL_MAP.keys()),
    )
    def test_example_roundtrip(self, filename: str, model_cls: type) -> None:
        """Deserialize → serialize → deserialize should produce equivalent objects."""
        example_path = EXAMPLES_DIR / filename
        raw_json = example_path.read_text()

        instance = model_cls.model_validate_json(raw_json)
        serialized = instance.model_dump_json()
        instance2 = model_cls.model_validate_json(serialized)

        assert instance == instance2


class TestSchemaFiles:
    """Validate that generated schema files are valid JSON and structurally correct."""

    @pytest.mark.parametrize(
        "filename,model_cls",
        list(SCHEMA_MODEL_MAP.items()),
        ids=list(SCHEMA_MODEL_MAP.keys()),
    )
    def test_schema_is_valid_json(self, filename: str, model_cls: type) -> None:
        """Each schema file should be valid JSON."""
        schema_path = SCHEMAS_DIR / filename
        assert schema_path.exists(), f"Schema file not found: {schema_path}"

        schema = json.loads(schema_path.read_text())
        assert isinstance(schema, dict)
        assert "properties" in schema or "$defs" in schema

    @pytest.mark.parametrize(
        "filename,model_cls",
        list(SCHEMA_MODEL_MAP.items()),
        ids=list(SCHEMA_MODEL_MAP.keys()),
    )
    def test_schema_matches_model(self, filename: str, model_cls: type) -> None:
        """Schema file content should match what Pydantic generates."""
        schema_path = SCHEMAS_DIR / filename
        file_schema = json.loads(schema_path.read_text())
        model_schema = model_cls.model_json_schema()

        assert file_schema == model_schema
