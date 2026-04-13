"""Generate JSON Schema files from Pydantic models."""

import json
from pathlib import Path

from m2la_contracts.analyze import AnalyzeRequest, AnalyzeResponse
from m2la_contracts.common import ArtifactManifest
from m2la_contracts.transform import TransformRequest, TransformResponse
from m2la_contracts.validate import ValidateRequest, ValidationReport

# Map of output filename to model class
SCHEMA_MODELS: dict[str, type] = {
    "analyze_request.schema.json": AnalyzeRequest,
    "analyze_response.schema.json": AnalyzeResponse,
    "transform_request.schema.json": TransformRequest,
    "transform_response.schema.json": TransformResponse,
    "validate_request.schema.json": ValidateRequest,
    "validation_report.schema.json": ValidationReport,
    "artifact_manifest.schema.json": ArtifactManifest,
}


def main() -> None:
    """Generate JSON schema files into the schemas/ directory."""
    schemas_dir = Path(__file__).resolve().parent.parent.parent.parent / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)

    for filename, model_cls in SCHEMA_MODELS.items():
        schema = model_cls.model_json_schema()
        output_path = schemas_dir / filename
        output_path.write_text(json.dumps(schema, indent=2) + "\n")
        print(f"Generated {output_path}")

    print(f"\nAll schemas written to {schemas_dir}")


if __name__ == "__main__":
    main()
