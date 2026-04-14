"""Tests: YAML config loading from real mapping-config package files."""

from __future__ import annotations

from pathlib import Path

import pytest

from m2la_mapping_config import (
    AuthPreferences,
    MappingConfig,
    load_all,
    load_auth_preferences,
    load_connector_mappings,
    load_construct_mappings,
)


class TestLoadConnectorMappings:
    def test_returns_non_empty_dict(self) -> None:
        """Connector mappings file should contain at least one entry."""
        mappings = load_connector_mappings()
        assert len(mappings) > 0

    def test_keys_are_strings(self) -> None:
        """All mapping keys (IDs) should be strings."""
        mappings = load_connector_mappings()
        for key in mappings:
            assert isinstance(key, str), f"Key {key!r} is not a string"

    def test_http_listener_present(self) -> None:
        """http-listener entry must be present in the connector mappings."""
        mappings = load_connector_mappings()
        assert "http-listener" in mappings

    def test_http_listener_fields(self) -> None:
        """http-listener entry must have correct namespace, element, and logic-apps fields."""
        mappings = load_connector_mappings()
        entry = mappings["http-listener"]
        assert entry.mule_namespace == "http://www.mulesoft.org/schema/mule/http"
        assert entry.mule_element == "listener"
        assert entry.logic_apps.type == "trigger"
        assert entry.logic_apps.kind == "Request"
        assert entry.logic_apps.connector_type == "built-in"

    def test_all_entries_have_required_fields(self) -> None:
        """Every connector entry should have non-empty namespace, element, and kind."""
        mappings = load_connector_mappings()
        for key, entry in mappings.items():
            assert entry.mule_namespace, f"{key}: mule_namespace is empty"
            assert entry.mule_element, f"{key}: mule_element is empty"
            assert entry.logic_apps.kind, f"{key}: logic_apps.kind is empty"
            assert entry.logic_apps.connector_type in ("built-in", "managed"), (
                f"{key}: unexpected connector_type {entry.logic_apps.connector_type!r}"
            )

    def test_auth_values_are_valid(self) -> None:
        """All auth values must be one of the allowed types."""
        valid_auth = {"managed-identity", "none", "api-key"}
        mappings = load_connector_mappings()
        for key, entry in mappings.items():
            assert entry.logic_apps.auth in valid_auth, f"{key}: unexpected auth value {entry.logic_apps.auth!r}"


class TestLoadConstructMappings:
    def test_returns_non_empty_dict(self) -> None:
        """Construct mappings file should contain at least one entry."""
        mappings = load_construct_mappings()
        assert len(mappings) > 0

    def test_choice_present(self) -> None:
        """'choice' entry must be present."""
        mappings = load_construct_mappings()
        assert "choice" in mappings

    def test_choice_is_supported(self) -> None:
        """'choice' must be supported with 'If' as the logic_apps_type."""
        mappings = load_construct_mappings()
        entry = mappings["choice"]
        assert entry.mule_element == "choice"
        assert entry.logic_apps_type == "If"
        assert entry.supported is True

    def test_logger_is_unsupported(self) -> None:
        """'logger' must be explicitly marked as unsupported."""
        mappings = load_construct_mappings()
        assert "logger" in mappings
        entry = mappings["logger"]
        assert entry.supported is False
        assert entry.logic_apps_type is None

    def test_dataweave_transform_present(self) -> None:
        """DataWeave transform entry must be present and use 'ee:transform' element name."""
        mappings = load_construct_mappings()
        assert "dataweave-transform" in mappings
        entry = mappings["dataweave-transform"]
        assert entry.mule_element == "ee:transform"
        assert entry.supported is True

    def test_all_supported_entries_have_logic_apps_type(self) -> None:
        """Every supported construct entry must have a non-null logic_apps_type."""
        mappings = load_construct_mappings()
        for key, entry in mappings.items():
            if entry.supported:
                assert entry.logic_apps_type is not None, f"{key}: supported=True but logic_apps_type is None"


class TestLoadAuthPreferences:
    def test_returns_auth_preferences(self) -> None:
        """load_auth_preferences should return an AuthPreferences instance."""
        prefs = load_auth_preferences()
        assert isinstance(prefs, AuthPreferences)

    def test_auth_priority_order(self) -> None:
        """managed-identity must come before none, and none before api-key."""
        prefs = load_auth_preferences()
        order = prefs.auth_priority
        assert "managed-identity" in order
        assert "none" in order
        assert "api-key" in order
        assert order.index("managed-identity") < order.index("none")
        assert order.index("none") < order.index("api-key")

    def test_connector_type_priority_order(self) -> None:
        """built-in must come before managed."""
        prefs = load_auth_preferences()
        order = prefs.connector_type_priority
        assert "built-in" in order
        assert "managed" in order
        assert order.index("built-in") < order.index("managed")


class TestLoadAll:
    def test_returns_mapping_config(self) -> None:
        """load_all should return a populated MappingConfig."""
        config = load_all()
        assert isinstance(config, MappingConfig)

    def test_connectors_non_empty(self) -> None:
        """MappingConfig.connectors should be non-empty."""
        config = load_all()
        assert len(config.connectors) > 0

    def test_constructs_non_empty(self) -> None:
        """MappingConfig.constructs should be non-empty."""
        config = load_all()
        assert len(config.constructs) > 0

    def test_auth_preferences_loaded(self) -> None:
        """MappingConfig.auth_preferences should have populated lists."""
        config = load_all()
        assert len(config.auth_preferences.auth_priority) > 0
        assert len(config.auth_preferences.connector_type_priority) > 0

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """load_all with a directory that has no YAML files should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_connector_mappings(tmp_path)
