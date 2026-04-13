"""Tests for common shared models."""

import pytest
from pydantic import ValidationError

from m2la_contracts.common import ArtifactEntry, ArtifactManifest, ConstructCount, MigrationGap, Warning
from m2la_contracts.enums import GapCategory, InputMode, Severity


class TestMigrationGap:
    """Tests for MigrationGap model."""

    def test_full_construction(self) -> None:
        gap = MigrationGap(
            construct_name="scatter-gather",
            source_location="flows/main.xml:42",
            category=GapCategory.UNSUPPORTED_CONSTRUCT,
            severity=Severity.ERROR,
            message="scatter-gather not supported",
            suggested_workaround="Use parallel branches",
        )
        assert gap.construct_name == "scatter-gather"
        assert gap.category == GapCategory.UNSUPPORTED_CONSTRUCT
        assert gap.suggested_workaround == "Use parallel branches"

    def test_optional_workaround_defaults_none(self) -> None:
        gap = MigrationGap(
            construct_name="test",
            source_location="test.xml:1",
            category=GapCategory.PARTIAL_SUPPORT,
            severity=Severity.WARNING,
            message="partial",
        )
        assert gap.suggested_workaround is None

    def test_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            MigrationGap(construct_name="test")  # type: ignore[call-arg]


class TestConstructCount:
    """Tests for ConstructCount model."""

    def test_defaults(self) -> None:
        cc = ConstructCount()
        assert cc.supported == 0
        assert cc.unsupported == 0
        assert cc.partial == 0
        assert cc.details == {}

    def test_with_values(self) -> None:
        cc = ConstructCount(supported=5, unsupported=2, partial=1, details={"http_listener": 2})
        assert cc.supported == 5
        assert cc.details["http_listener"] == 2

    def test_negative_values_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ConstructCount(supported=-1)


class TestWarning:
    """Tests for Warning model."""

    def test_default_severity(self) -> None:
        w = Warning(code="TEST_001", message="test warning")
        assert w.severity == Severity.WARNING
        assert w.source_location is None

    def test_custom_severity(self) -> None:
        w = Warning(code="TEST_002", message="info msg", severity=Severity.INFO, source_location="file.xml:10")
        assert w.severity == Severity.INFO
        assert w.source_location == "file.xml:10"


class TestArtifactEntry:
    """Tests for ArtifactEntry model."""

    def test_basic(self) -> None:
        entry = ArtifactEntry(path="workflows/main/workflow.json", artifact_type="workflow")
        assert entry.path == "workflows/main/workflow.json"
        assert entry.size_bytes is None

    def test_with_size(self) -> None:
        entry = ArtifactEntry(path="host.json", artifact_type="host_json", size_bytes=1024)
        assert entry.size_bytes == 1024

    def test_negative_size_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ArtifactEntry(path="x", artifact_type="y", size_bytes=-1)


class TestArtifactManifest:
    """Tests for ArtifactManifest model."""

    def test_empty_manifest(self) -> None:
        manifest = ArtifactManifest(output_directory="./output", mode=InputMode.PROJECT)
        assert manifest.artifacts == []
        assert manifest.output_directory == "./output"
        assert manifest.mode == InputMode.PROJECT

    def test_with_artifacts(self) -> None:
        entry = ArtifactEntry(path="workflow.json", artifact_type="workflow")
        manifest = ArtifactManifest(
            artifacts=[entry],
            output_directory="./out",
            mode=InputMode.SINGLE_FLOW,
        )
        assert len(manifest.artifacts) == 1
        assert manifest.mode == InputMode.SINGLE_FLOW
