"""Tests for top-level __init__ re-exports."""

import m2la_contracts


class TestReExports:
    """Verify that all public symbols are accessible from the top-level package."""

    def test_enums(self) -> None:
        assert hasattr(m2la_contracts, "InputMode")
        assert hasattr(m2la_contracts, "Severity")
        assert hasattr(m2la_contracts, "GapCategory")
        assert hasattr(m2la_contracts, "ConstructCategory")

    def test_telemetry(self) -> None:
        assert hasattr(m2la_contracts, "TelemetryContext")

    def test_common_models(self) -> None:
        assert hasattr(m2la_contracts, "MigrationGap")
        assert hasattr(m2la_contracts, "ConstructCount")
        assert hasattr(m2la_contracts, "Warning")
        assert hasattr(m2la_contracts, "ArtifactEntry")
        assert hasattr(m2la_contracts, "ArtifactManifest")

    def test_analyze_models(self) -> None:
        assert hasattr(m2la_contracts, "AnalyzeRequest")
        assert hasattr(m2la_contracts, "AnalyzeResponse")
        assert hasattr(m2la_contracts, "FlowAnalysis")

    def test_transform_models(self) -> None:
        assert hasattr(m2la_contracts, "TransformRequest")
        assert hasattr(m2la_contracts, "TransformResponse")

    def test_validate_models(self) -> None:
        assert hasattr(m2la_contracts, "ValidationIssue")
        assert hasattr(m2la_contracts, "ValidationReport")

    def test_helpers(self) -> None:
        assert hasattr(m2la_contracts, "detect_input_mode")

    def test_all_list_complete(self) -> None:
        """Verify __all__ contains the expected number of exports."""
        assert len(m2la_contracts.__all__) == 18
