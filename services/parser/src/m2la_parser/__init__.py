"""MuleSoft project and flow XML parsing for the migration platform.

This package provides parsing logic for MuleSoft/Anypoint projects and
standalone flow XML files, producing a normalized ProjectInventory model.
"""

from m2la_parser.models import (
    ConnectorConfig,
    GlobalElement,
    MuleFlow,
    MuleFlowFile,
    MuleSubFlow,
    ProcessorElement,
    ProjectInventory,
    ProjectMetadata,
    PropertyFile,
)
from m2la_parser.parse import parse

__all__ = [
    "ConnectorConfig",
    "GlobalElement",
    "MuleFlow",
    "MuleFlowFile",
    "MuleSubFlow",
    "ProcessorElement",
    "ProjectInventory",
    "ProjectMetadata",
    "PropertyFile",
    "parse",
]
