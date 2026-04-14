"""m2la-mapping-config — externalized connector and construct mapping config.

Public exports
--------------
Models:
    MappingConfig, ConnectorMappingEntry, ConstructMappingEntry, AuthPreferences

Resolver:
    MappingResolver

Loader functions:
    load_all, load_connector_mappings, load_construct_mappings, load_auth_preferences
"""

from __future__ import annotations

from m2la_mapping_config.loader import (
    load_all,
    load_auth_preferences,
    load_connector_mappings,
    load_construct_mappings,
)
from m2la_mapping_config.models import (
    AuthPreferences,
    ConnectorMappingEntry,
    ConstructMappingEntry,
    MappingConfig,
)
from m2la_mapping_config.resolver import MappingResolver

__all__ = [
    # Models
    "AuthPreferences",
    "ConnectorMappingEntry",
    "ConstructMappingEntry",
    "MappingConfig",
    # Resolver
    "MappingResolver",
    # Loader functions
    "load_all",
    "load_auth_preferences",
    "load_connector_mappings",
    "load_construct_mappings",
]
