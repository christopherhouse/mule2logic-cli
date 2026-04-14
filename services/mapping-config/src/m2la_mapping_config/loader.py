"""YAML config loader for connector and construct mapping files.

By default, configs are loaded from the canonical ``packages/mapping-config/``
directory at the repository root, resolved relative to this module file.

Directory layout (from repo root)::

    packages/
        mapping-config/
            connector_mappings.yaml
            construct_mappings.yaml
            auth_preferences.yaml
    services/
        mapping-config/
            src/
                m2la_mapping_config/
                    loader.py   ← this file
"""

from __future__ import annotations

from pathlib import Path

import yaml

from m2la_mapping_config.models import (
    AuthPreferences,
    ConnectorMappingEntry,
    ConstructMappingEntry,
    MappingConfig,
)

# ---------------------------------------------------------------------------
# Default config directory
# ---------------------------------------------------------------------------

# Traverse up from this file to the repository root, then into packages/mapping-config/.
# Path: loader.py → m2la_mapping_config/ → src/ → mapping-config/ → services/ → repo root
_THIS_FILE = Path(__file__)
_REPO_ROOT = _THIS_FILE.parent.parent.parent.parent.parent
_DEFAULT_CONFIG_DIR: Path = _REPO_ROOT / "packages" / "mapping-config"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_connector_mappings(config_dir: Path = _DEFAULT_CONFIG_DIR) -> dict[str, ConnectorMappingEntry]:
    """Load connector mappings from ``connector_mappings.yaml``.

    Args:
        config_dir: Directory containing the YAML config files.
                    Defaults to ``packages/mapping-config/`` at the repo root.

    Returns:
        A dict keyed by mapping ID (label from YAML) → :class:`ConnectorMappingEntry`.

    Raises:
        FileNotFoundError: If the YAML file does not exist at *config_dir*.
        ValueError: If the YAML structure is invalid or required fields are missing.
    """
    path = config_dir / "connector_mappings.yaml"
    raw = _read_yaml(path)
    connectors_raw: dict[str, object] = raw.get("connectors", {})
    return {key: ConnectorMappingEntry.model_validate(value) for key, value in connectors_raw.items()}


def load_construct_mappings(config_dir: Path = _DEFAULT_CONFIG_DIR) -> dict[str, ConstructMappingEntry]:
    """Load construct mappings from ``construct_mappings.yaml``.

    Args:
        config_dir: Directory containing the YAML config files.

    Returns:
        A dict keyed by mapping ID → :class:`ConstructMappingEntry`.

    Raises:
        FileNotFoundError: If the YAML file does not exist at *config_dir*.
        ValueError: If the YAML structure is invalid or required fields are missing.
    """
    path = config_dir / "construct_mappings.yaml"
    raw = _read_yaml(path)
    constructs_raw: dict[str, object] = raw.get("constructs", {})
    return {key: ConstructMappingEntry.model_validate(value) for key, value in constructs_raw.items()}


def load_auth_preferences(config_dir: Path = _DEFAULT_CONFIG_DIR) -> AuthPreferences:
    """Load auth preference rankings from ``auth_preferences.yaml``.

    Args:
        config_dir: Directory containing the YAML config files.

    Returns:
        An :class:`AuthPreferences` instance.

    Raises:
        FileNotFoundError: If the YAML file does not exist at *config_dir*.
        ValueError: If the YAML structure is invalid or required fields are missing.
    """
    path = config_dir / "auth_preferences.yaml"
    raw = _read_yaml(path)
    return AuthPreferences.model_validate(raw)


def load_all(config_dir: Path = _DEFAULT_CONFIG_DIR) -> MappingConfig:
    """Load all mapping configs and return an aggregated :class:`MappingConfig`.

    Args:
        config_dir: Directory containing the YAML config files.

    Returns:
        A :class:`MappingConfig` with connectors, constructs, and auth preferences populated.
    """
    return MappingConfig(
        connectors=load_connector_mappings(config_dir),
        constructs=load_construct_mappings(config_dir),
        auth_preferences=load_auth_preferences(config_dir),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_yaml(path: Path) -> dict[str, object]:
    """Read and parse a YAML file, returning its contents as a dict.

    Args:
        path: Absolute path to the YAML file.

    Returns:
        Parsed YAML content as a plain Python dict.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If the YAML content is not a mapping at the top level.
    """
    if not path.exists():
        raise FileNotFoundError(f"Mapping config file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        content = yaml.safe_load(fh)
    if not isinstance(content, dict):
        raise ValueError(f"Expected a YAML mapping at the top level of {path}, got {type(content).__name__}")
    return content
