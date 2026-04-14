"""Tests: MappingResolver lookup behaviour using real config data."""

from __future__ import annotations

import pytest

from m2la_mapping_config import (
    MappingResolver,
    load_all,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HTTP_NS = "http://www.mulesoft.org/schema/mule/http"
SFTP_NS = "http://www.mulesoft.org/schema/mule/sftp"
FTP_NS = "http://www.mulesoft.org/schema/mule/ftp"
JMS_NS = "http://www.mulesoft.org/schema/mule/jms"
DB_NS = "http://www.mulesoft.org/schema/mule/db"
CORE_NS = "http://www.mulesoft.org/schema/mule/core"


@pytest.fixture(scope="module")
def resolver() -> MappingResolver:
    """Return a MappingResolver built from the real YAML config files."""
    return MappingResolver(load_all())


# ---------------------------------------------------------------------------
# Connector resolution
# ---------------------------------------------------------------------------


class TestResolveConnector:
    def test_exact_match_http_listener(self, resolver: MappingResolver) -> None:
        """http-listener should resolve to the Request trigger (built-in)."""
        entry = resolver.resolve_connector(HTTP_NS, "listener")
        assert entry is not None
        assert entry.logic_apps.kind == "Request"
        assert entry.logic_apps.type == "trigger"
        assert entry.logic_apps.connector_type == "built-in"

    def test_exact_match_http_request(self, resolver: MappingResolver) -> None:
        """http-request should resolve to the Http action (built-in)."""
        entry = resolver.resolve_connector(HTTP_NS, "request")
        assert entry is not None
        assert entry.logic_apps.kind == "Http"
        assert entry.logic_apps.type == "action"
        assert entry.logic_apps.connector_type == "built-in"

    def test_exact_match_scheduler(self, resolver: MappingResolver) -> None:
        """scheduler should resolve to the Recurrence trigger."""
        entry = resolver.resolve_connector(CORE_NS, "scheduler")
        assert entry is not None
        assert entry.logic_apps.kind == "Recurrence"
        assert entry.logic_apps.type == "trigger"

    def test_exact_match_db_select(self, resolver: MappingResolver) -> None:
        """db select should resolve to SqlServerQuery (built-in, managed-identity)."""
        entry = resolver.resolve_connector(DB_NS, "select")
        assert entry is not None
        assert entry.logic_apps.kind == "SqlServerQuery"
        assert entry.logic_apps.connector_type == "built-in"
        assert entry.logic_apps.auth == "managed-identity"

    def test_wildcard_resolution_sftp(self, resolver: MappingResolver) -> None:
        """Any SFTP element should resolve via the wildcard entry to the Sftp built-in connector."""
        # "write" is not defined as an exact entry, so must fall back to wildcard
        entry = resolver.resolve_connector(SFTP_NS, "write")
        assert entry is not None
        assert entry.logic_apps.kind == "Sftp"
        assert entry.logic_apps.connector_type == "built-in"
        assert entry.logic_apps.auth == "managed-identity"

    def test_wildcard_resolution_ftp(self, resolver: MappingResolver) -> None:
        """Any FTP element should resolve via wildcard to the Sftp connector."""
        entry = resolver.resolve_connector(FTP_NS, "read")
        assert entry is not None
        assert entry.logic_apps.kind == "Sftp"

    def test_wildcard_resolution_jms(self, resolver: MappingResolver) -> None:
        """Any JMS element should resolve via wildcard to ServiceBus."""
        entry = resolver.resolve_connector(JMS_NS, "publish")
        assert entry is not None
        assert entry.logic_apps.kind == "ServiceBus"
        assert entry.logic_apps.connector_type == "built-in"

    def test_unknown_namespace_returns_none(self, resolver: MappingResolver) -> None:
        """An unrecognised namespace should return None, not raise an error."""
        entry = resolver.resolve_connector("http://unknown.example.com/ns", "something")
        assert entry is None

    def test_unknown_element_in_known_namespace_returns_none(self, resolver: MappingResolver) -> None:
        """An exact lookup for an element with no exact or wildcard entry returns None."""
        # HTTP namespace has exact entries but no wildcard; "unknown-op" should miss
        entry = resolver.resolve_connector(HTTP_NS, "unknown-op")
        assert entry is None

    def test_result_is_connector_mapping_entry(self, resolver: MappingResolver) -> None:
        """Resolved entry should be a ConnectorMappingEntry instance."""
        from m2la_mapping_config import ConnectorMappingEntry

        entry = resolver.resolve_connector(HTTP_NS, "listener")
        assert isinstance(entry, ConnectorMappingEntry)


# ---------------------------------------------------------------------------
# Construct resolution
# ---------------------------------------------------------------------------


class TestResolveConstruct:
    def test_choice_resolved(self, resolver: MappingResolver) -> None:
        """'choice' should resolve to an 'If' construct."""
        entry = resolver.resolve_construct("choice")
        assert entry is not None
        assert entry.logic_apps_type == "If"
        assert entry.supported is True

    def test_foreach_resolved(self, resolver: MappingResolver) -> None:
        """'foreach' should resolve to a 'Foreach' construct."""
        entry = resolver.resolve_construct("foreach")
        assert entry is not None
        assert entry.logic_apps_type == "Foreach"

    def test_scatter_gather_resolved(self, resolver: MappingResolver) -> None:
        """'scatter-gather' should resolve to 'Parallel'."""
        entry = resolver.resolve_construct("scatter-gather")
        assert entry is not None
        assert entry.logic_apps_type == "Parallel"

    def test_dataweave_transform_resolved(self, resolver: MappingResolver) -> None:
        """'ee:transform' should resolve to the DataWeave/Compose mapping."""
        entry = resolver.resolve_construct("ee:transform")
        assert entry is not None
        assert entry.logic_apps_type == "Compose"
        assert entry.supported is True

    def test_logger_resolved_unsupported(self, resolver: MappingResolver) -> None:
        """'logger' should resolve but be marked unsupported with no logic_apps_type."""
        entry = resolver.resolve_construct("logger")
        assert entry is not None
        assert entry.supported is False
        assert entry.logic_apps_type is None

    def test_unknown_construct_returns_none(self, resolver: MappingResolver) -> None:
        """An unrecognised element name should return None, not raise."""
        entry = resolver.resolve_construct("totally-unknown-element")
        assert entry is None

    def test_result_is_construct_mapping_entry(self, resolver: MappingResolver) -> None:
        """Resolved entry should be a ConstructMappingEntry."""
        from m2la_mapping_config import ConstructMappingEntry

        entry = resolver.resolve_construct("choice")
        assert isinstance(entry, ConstructMappingEntry)


# ---------------------------------------------------------------------------
# is_supported
# ---------------------------------------------------------------------------


class TestIsSupported:
    def test_known_supported_element(self, resolver: MappingResolver) -> None:
        """'foreach' is a known supported element."""
        assert resolver.is_supported("foreach") is True

    def test_known_unsupported_element(self, resolver: MappingResolver) -> None:
        """'logger' is explicitly unsupported."""
        assert resolver.is_supported("logger") is False

    def test_unknown_element_is_not_supported(self, resolver: MappingResolver) -> None:
        """An element with no mapping entry is not considered supported."""
        assert resolver.is_supported("nonexistent-element") is False

    def test_ee_transform_is_supported(self, resolver: MappingResolver) -> None:
        """'ee:transform' should be supported."""
        assert resolver.is_supported("ee:transform") is True

    def test_set_variable_is_supported(self, resolver: MappingResolver) -> None:
        """'set-variable' should be supported."""
        assert resolver.is_supported("set-variable") is True
