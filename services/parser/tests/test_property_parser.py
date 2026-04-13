"""Tests for ``m2la_parser.property_parser.parse_properties_file``."""

from pathlib import Path

from m2la_parser.property_parser import parse_properties_file


class TestParseValidProperties:
    """Verify parsing of application.properties from the hello-world-project."""

    def test_parse_valid_properties(self, hello_world_project: Path) -> None:
        props_path = hello_world_project / "src" / "main" / "resources" / "application.properties"
        pf, warnings = parse_properties_file(props_path, relative_to=hello_world_project)

        assert pf.properties["http.port"] == "8081"
        assert pf.properties["greeting.message"] == "Hello, World!"
        assert pf.properties["api.host"] == "api.example.com"
        assert pf.properties["api.port"] == "443"
        assert pf.properties["db.host"] == "localhost"
        assert pf.properties["db.port"] == "3306"
        assert pf.properties["db.user"] == "admin"
        assert pf.properties["db.password"] == "changeme"
        assert pf.properties["db.name"] == "mydb"

        # No meaningful warnings on a well-formed file
        assert all(w.code != "MISSING_PROPERTY_FILE" for w in warnings)


class TestParseDevProperties:
    """Verify parsing of application-dev.properties with overrides."""

    def test_parse_dev_properties(self, hello_world_project: Path) -> None:
        props_path = hello_world_project / "src" / "main" / "resources" / "application-dev.properties"
        pf, warnings = parse_properties_file(props_path, relative_to=hello_world_project)

        assert pf.properties["http.port"] == "8082"
        assert pf.properties["api.host"] == "dev-api.example.com"
        assert pf.properties["db.host"] == "dev-db.example.com"


class TestMissingPropertiesFile:
    """Verify warning for a missing properties file."""

    def test_missing_properties_file(self, tmp_path: Path) -> None:
        pf, warnings = parse_properties_file(tmp_path / "nonexistent.properties")

        assert pf.properties == {}
        assert len(warnings) == 1
        assert warnings[0].code == "MISSING_PROPERTY_FILE"


class TestEmptyPropertiesFile:
    """Verify parsing of an empty properties file."""

    def test_empty_properties_file(self, tmp_path: Path) -> None:
        empty_file = tmp_path / "empty.properties"
        empty_file.write_text("", encoding="utf-8")

        pf, warnings = parse_properties_file(empty_file)

        assert pf.properties == {}
        # No warnings for an empty but valid file
        assert all(w.code != "MISSING_PROPERTY_FILE" for w in warnings)
