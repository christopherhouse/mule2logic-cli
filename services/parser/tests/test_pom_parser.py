"""Tests for ``m2la_parser.pom_parser.parse_pom``."""

from pathlib import Path

from m2la_parser.pom_parser import parse_pom


class TestParseValidPom:
    """Verify correct extraction from the hello-world-project pom.xml."""

    def test_parse_valid_pom(self, hello_world_project: Path) -> None:
        pom_path = hello_world_project / "pom.xml"
        metadata, warnings = parse_pom(pom_path)

        assert metadata is not None
        assert metadata.group_id == "com.example"
        assert metadata.artifact_id == "hello-world-app"
        assert metadata.version == "1.0.0"
        assert metadata.mule_version == "4.4.0"

        # Connector dependencies
        assert "mule-http-connector" in metadata.connector_dependencies
        assert "mule-db-connector" in metadata.connector_dependencies
        assert "mule-apikit-module" in metadata.connector_dependencies
        assert "mule-secure-configuration-property-module" in metadata.connector_dependencies

        # No warnings for a valid pom
        assert warnings == []


class TestParseMissingPom:
    """Verify behaviour when pom.xml does not exist."""

    def test_parse_missing_pom(self, tmp_path: Path) -> None:
        metadata, warnings = parse_pom(tmp_path / "nonexistent" / "pom.xml")

        assert metadata is None
        assert len(warnings) == 1
        assert warnings[0].code == "MISSING_POM"


class TestParseMalformedPom:
    """Verify behaviour when pom.xml contains invalid XML."""

    def test_parse_malformed_pom(self, tmp_path: Path) -> None:
        bad_pom = tmp_path / "pom.xml"
        bad_pom.write_text("<project><groupId>bad</groupId><!-- unclosed", encoding="utf-8")

        metadata, warnings = parse_pom(bad_pom)

        assert metadata is None
        assert len(warnings) == 1
        assert warnings[0].code == "MALFORMED_POM"
