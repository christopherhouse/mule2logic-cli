"""Tests: rank_connectors with synthetic data to directly verify priority ordering."""

from __future__ import annotations

from m2la_mapping_config import (
    AuthPreferences,
    ConnectorMappingEntry,
    MappingConfig,
    MappingResolver,
)
from m2la_mapping_config.models import (
    ConstructMappingEntry,
    LogicAppsMapping,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AUTH_PREFS = AuthPreferences(
    auth_priority=["managed-identity", "none", "api-key"],
    connector_type_priority=["built-in", "managed"],
)


def _make_entry(connector_type: str, auth: str, element: str = "op") -> ConnectorMappingEntry:
    """Construct a synthetic ConnectorMappingEntry for testing."""
    return ConnectorMappingEntry(
        mule_namespace="http://example.com/ns",
        mule_element=element,
        logic_apps=LogicAppsMapping(
            type="action",
            kind="TestKind",
            connector_type=connector_type,
            auth=auth,
        ),
    )


def _make_resolver(*entries: ConnectorMappingEntry) -> MappingResolver:
    """Build a MappingResolver with the given synthetic entries and default auth prefs."""
    connectors = {f"entry-{i}": e for i, e in enumerate(entries)}
    config = MappingConfig(
        connectors=connectors,
        constructs={},
        auth_preferences=_AUTH_PREFS,
    )
    return MappingResolver(config)


# ---------------------------------------------------------------------------
# Priority ranking tests
# ---------------------------------------------------------------------------


class TestRankConnectors:
    def test_builtin_managed_identity_beats_builtin_api_key(self) -> None:
        """built-in+managed-identity must rank above built-in+api-key."""
        winner = _make_entry("built-in", "managed-identity")
        loser = _make_entry("built-in", "api-key")
        resolver = _make_resolver(loser, winner)  # intentionally wrong order

        ranked = resolver.rank_connectors([loser, winner])
        assert ranked[0] is winner
        assert ranked[1] is loser

    def test_builtin_managed_identity_beats_managed_managed_identity(self) -> None:
        """built-in+managed-identity must rank above managed+managed-identity."""
        winner = _make_entry("built-in", "managed-identity")
        loser = _make_entry("managed", "managed-identity")
        resolver = _make_resolver(winner, loser)

        ranked = resolver.rank_connectors([loser, winner])
        assert ranked[0] is winner
        assert ranked[1] is loser

    def test_builtin_api_key_beats_managed_managed_identity(self) -> None:
        """built-in+api-key must rank above managed+managed-identity (connector_type wins)."""
        winner = _make_entry("built-in", "api-key")
        loser = _make_entry("managed", "managed-identity")
        resolver = _make_resolver(loser, winner)

        ranked = resolver.rank_connectors([loser, winner])
        assert ranked[0] is winner
        assert ranked[1] is loser

    def test_managed_managed_identity_beats_managed_api_key(self) -> None:
        """managed+managed-identity must rank above managed+api-key."""
        winner = _make_entry("managed", "managed-identity")
        loser = _make_entry("managed", "api-key")
        resolver = _make_resolver(loser, winner)

        ranked = resolver.rank_connectors([loser, winner])
        assert ranked[0] is winner
        assert ranked[1] is loser

    def test_stable_sort_for_equal_ranking(self) -> None:
        """Entries with identical connector_type and auth should preserve original order."""
        a = _make_entry("built-in", "managed-identity", element="a")
        b = _make_entry("built-in", "managed-identity", element="b")
        c = _make_entry("built-in", "managed-identity", element="c")
        resolver = _make_resolver(a, b, c)

        ranked = resolver.rank_connectors([a, b, c])
        # All are equal; stable sort must keep the original insertion order
        assert ranked[0] is a
        assert ranked[1] is b
        assert ranked[2] is c

    def test_empty_list_returns_empty(self) -> None:
        """rank_connectors with an empty list should return an empty list."""
        resolver = _make_resolver()
        assert resolver.rank_connectors([]) == []

    def test_single_entry_returns_same_entry(self) -> None:
        """rank_connectors with a single entry should return that entry unchanged."""
        entry = _make_entry("managed", "api-key")
        resolver = _make_resolver(entry)
        ranked = resolver.rank_connectors([entry])
        assert len(ranked) == 1
        assert ranked[0] is entry

    def test_full_priority_order(self) -> None:
        """Verify full descending priority across all combinations."""
        bi_mi = _make_entry("built-in", "managed-identity", element="bi_mi")
        bi_none = _make_entry("built-in", "none", element="bi_none")
        bi_ak = _make_entry("built-in", "api-key", element="bi_ak")
        mg_mi = _make_entry("managed", "managed-identity", element="mg_mi")
        mg_none = _make_entry("managed", "none", element="mg_none")
        mg_ak = _make_entry("managed", "api-key", element="mg_ak")

        resolver = _make_resolver(mg_ak, mg_none, mg_mi, bi_ak, bi_none, bi_mi)
        ranked = resolver.rank_connectors([mg_ak, mg_none, mg_mi, bi_ak, bi_none, bi_mi])

        assert ranked[0] is bi_mi
        assert ranked[1] is bi_none
        assert ranked[2] is bi_ak
        assert ranked[3] is mg_mi
        assert ranked[4] is mg_none
        assert ranked[5] is mg_ak


# ---------------------------------------------------------------------------
# Resolver integration with synthetic data
# ---------------------------------------------------------------------------


class TestResolverWithSyntheticData:
    def test_exact_beats_wildcard(self) -> None:
        """Exact element match must beat wildcard match, even if wildcard has higher auth priority."""
        ns = "http://example.com/ns"
        exact_entry = _make_entry("managed", "api-key", element="op")
        # Override namespace
        exact_entry = ConnectorMappingEntry(
            mule_namespace=ns,
            mule_element="op",
            logic_apps=LogicAppsMapping(type="action", kind="Exact", connector_type="managed", auth="api-key"),
        )
        wildcard_entry = ConnectorMappingEntry(
            mule_namespace=ns,
            mule_element="*",
            logic_apps=LogicAppsMapping(
                type="action", kind="Wildcard", connector_type="built-in", auth="managed-identity"
            ),
        )

        config = MappingConfig(
            connectors={"exact": exact_entry, "wildcard": wildcard_entry},
            constructs={},
            auth_preferences=_AUTH_PREFS,
        )
        resolver = MappingResolver(config)

        result = resolver.resolve_connector(ns, "op")
        # Exact match should win regardless of ranking
        assert result is not None
        assert result.logic_apps.kind == "Exact"

    def test_wildcard_used_when_no_exact_match(self) -> None:
        """When no exact element match exists, wildcard entry should be returned."""
        ns = "http://example.com/ns"
        wildcard_entry = ConnectorMappingEntry(
            mule_namespace=ns,
            mule_element="*",
            logic_apps=LogicAppsMapping(
                type="action", kind="Wildcard", connector_type="built-in", auth="managed-identity"
            ),
        )

        config = MappingConfig(
            connectors={"wildcard": wildcard_entry},
            constructs={},
            auth_preferences=_AUTH_PREFS,
        )
        resolver = MappingResolver(config)

        result = resolver.resolve_connector(ns, "any-element")
        assert result is not None
        assert result.logic_apps.kind == "Wildcard"

    def test_construct_lookup_with_synthetic_data(self) -> None:
        """resolve_construct should find entries by mule_element, not by dict key."""
        construct_entry = ConstructMappingEntry(
            mule_element="my-element",
            logic_apps_type="MyAction",
            supported=True,
        )
        config = MappingConfig(
            connectors={},
            constructs={"any-key": construct_entry},
            auth_preferences=_AUTH_PREFS,
        )
        resolver = MappingResolver(config)

        result = resolver.resolve_construct("my-element")
        assert result is not None
        assert result.logic_apps_type == "MyAction"

    def test_unknown_construct_returns_none_synthetic(self) -> None:
        """resolve_construct should return None for an unknown element."""
        config = MappingConfig(
            connectors={},
            constructs={},
            auth_preferences=_AUTH_PREFS,
        )
        resolver = MappingResolver(config)
        assert resolver.resolve_construct("ghost-element") is None

    def test_is_supported_false_for_unsupported_construct(self) -> None:
        """is_supported should return False when supported=False."""
        construct_entry = ConstructMappingEntry(
            mule_element="bad-elem",
            logic_apps_type=None,
            supported=False,
        )
        config = MappingConfig(
            connectors={},
            constructs={"bad": construct_entry},
            auth_preferences=_AUTH_PREFS,
        )
        resolver = MappingResolver(config)
        assert resolver.is_supported("bad-elem") is False
