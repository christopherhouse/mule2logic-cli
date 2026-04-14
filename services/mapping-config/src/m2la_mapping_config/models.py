"""Pydantic models for connector and construct mapping configuration."""

from __future__ import annotations

from pydantic import BaseModel


class LogicAppsMapping(BaseModel):
    """Logic Apps target descriptor within a connector mapping entry."""

    type: str
    """Action kind: "trigger" or "action"."""

    kind: str
    """Logic Apps kind string (e.g. "Request", "Http", "Recurrence", "ServiceBus")."""

    connector_type: str
    """Connector category: "built-in" (serviceProviderConnections) or "managed" (managedApiConnections)."""

    auth: str = "none"
    """Authentication scheme: "managed-identity" | "none" | "api-key"."""

    notes: str | None = None
    """Optional human-readable notes about limitations or migration caveats."""


class ConnectorMappingEntry(BaseModel):
    """A single MuleSoft connector → Logic Apps connector mapping."""

    mule_namespace: str
    """The Mule XML namespace URI for the connector."""

    mule_element: str
    """The element local name within the namespace. Use "*" as a wildcard to match any element."""

    logic_apps: LogicAppsMapping
    """The corresponding Logic Apps connector descriptor."""


class ConstructMappingEntry(BaseModel):
    """A single MuleSoft control-flow construct → Logic Apps construct mapping."""

    mule_element: str
    """Mule XML element local name (may include a namespace prefix, e.g. "ee:transform")."""

    logic_apps_type: str | None
    """Logic Apps action/trigger type string, or None if no direct equivalent exists."""

    supported: bool
    """Whether automated conversion is supported for this construct."""

    notes: str | None = None
    """Optional human-readable notes about limitations or conversion caveats."""


class AuthPreferences(BaseModel):
    """Auth preference ranking rules loaded from auth_preferences.yaml."""

    auth_priority: list[str]
    """Ordered list of auth types from most to least preferred (e.g. ["managed-identity", "none", "api-key"])."""

    connector_type_priority: list[str]
    """Ordered list of connector types from most to least preferred (e.g. ["built-in", "managed"])."""


class MappingConfig(BaseModel):
    """Aggregated mapping configuration holding all connector, construct, and auth preference data."""

    connectors: dict[str, ConnectorMappingEntry]
    """Keyed by mapping ID (arbitrary string label used in the YAML file)."""

    constructs: dict[str, ConstructMappingEntry]
    """Keyed by mapping ID (arbitrary string label used in the YAML file)."""

    auth_preferences: AuthPreferences
    """Auth and connector-type priority ranking rules."""
