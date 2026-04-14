"""Mapping resolver — resolves MuleSoft elements to Logic Apps equivalents.

Resolution algorithm
--------------------
For **connectors**:

1. Collect all connector entries whose ``mule_namespace`` matches.
2. Within that set, prefer an *exact* ``mule_element`` match over a wildcard (``"*"``).
3. If multiple candidates survive, rank them by priority:
   - ``connector_type``: ``"built-in"`` > ``"managed"``
   - ``auth``: ``"managed-identity"`` > ``"none"`` > ``"api-key"``
4. Return the top-ranked candidate, or ``None`` if no match found.

For **constructs**:

1. Search all construct entries for an exact ``mule_element`` match.
2. Return the first match, or ``None``.
"""

from __future__ import annotations

from m2la_mapping_config.models import (
    AuthPreferences,
    ConnectorMappingEntry,
    ConstructMappingEntry,
    MappingConfig,
)


class MappingResolver:
    """Resolves MuleSoft elements to Logic Apps equivalents using loaded :class:`MappingConfig`."""

    def __init__(self, config: MappingConfig) -> None:
        self._config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_connector(
        self,
        mule_namespace: str,
        mule_element: str,
    ) -> ConnectorMappingEntry | None:
        """Find the best connector mapping for a given Mule namespace + element pair.

        Exact ``mule_element`` matches take precedence over wildcard (``"*"``) entries.
        Among multiple candidates, priority rules are applied (built-in first, then
        managed-identity first) via :meth:`rank_connectors`.

        Args:
            mule_namespace: The Mule XML namespace URI of the element.
            mule_element: The local name of the Mule XML element.

        Returns:
            The best-ranked :class:`ConnectorMappingEntry`, or ``None`` if not found.
        """
        exact: list[ConnectorMappingEntry] = []
        wildcards: list[ConnectorMappingEntry] = []

        for entry in self._config.connectors.values():
            if entry.mule_namespace != mule_namespace:
                continue
            if entry.mule_element == mule_element:
                exact.append(entry)
            elif entry.mule_element == "*":
                wildcards.append(entry)

        # Prefer exact matches; fall back to wildcards only when no exact match exists.
        candidates = exact if exact else wildcards
        if not candidates:
            return None

        ranked = self.rank_connectors(candidates)
        return ranked[0]

    def resolve_construct(
        self,
        mule_element: str,
    ) -> ConstructMappingEntry | None:
        """Find a construct mapping by Mule element name.

        Args:
            mule_element: The local name of the Mule XML element (may include a
                          namespace prefix such as ``"ee:transform"``).

        Returns:
            The matching :class:`ConstructMappingEntry`, or ``None`` if not found.
        """
        for entry in self._config.constructs.values():
            if entry.mule_element == mule_element:
                return entry
        return None

    def rank_connectors(
        self,
        candidates: list[ConnectorMappingEntry],
    ) -> list[ConnectorMappingEntry]:
        """Sort connector candidates by priority rules.

        Ranking criteria (lower index = higher priority):

        1. ``connector_type``: ordered by :attr:`AuthPreferences.connector_type_priority`
           (``"built-in"`` before ``"managed"``).
        2. ``auth``: ordered by :attr:`AuthPreferences.auth_priority`
           (``"managed-identity"`` before ``"none"`` before ``"api-key"``).

        The sort is stable — equal-ranked entries preserve their original order.

        Args:
            candidates: A list of connector entries to rank.

        Returns:
            A new list sorted from highest to lowest priority.
        """
        prefs: AuthPreferences = self._config.auth_preferences
        ct_order = prefs.connector_type_priority
        auth_order = prefs.auth_priority

        def _sort_key(entry: ConnectorMappingEntry) -> tuple[int, int]:
            ct = entry.logic_apps.connector_type
            ct_rank = ct_order.index(ct) if ct in ct_order else len(ct_order)
            auth = entry.logic_apps.auth
            auth_rank = auth_order.index(auth) if auth in auth_order else len(auth_order)
            return (ct_rank, auth_rank)

        return sorted(candidates, key=_sort_key)

    def is_supported(self, mule_element: str) -> bool:
        """Return ``True`` if the element has a supported construct mapping.

        Args:
            mule_element: The local name of the Mule XML element.

        Returns:
            ``True`` if a construct entry exists and its ``supported`` flag is ``True``;
            ``False`` otherwise (including when no entry is found).
        """
        entry = self.resolve_construct(mule_element)
        return entry is not None and entry.supported
