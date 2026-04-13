"""Public parse entry point for the MuleSoft parser."""

from pathlib import Path

from m2la_contracts.enums import InputMode
from m2la_contracts.helpers import detect_input_mode

from m2la_parser.models import ProjectInventory
from m2la_parser.project_discovery import discover_project
from m2la_parser.single_flow import parse_single_flow


def parse(input_path: str, mode: InputMode | None = None) -> ProjectInventory:
    """Parse a MuleSoft project or standalone flow XML.

    Auto-detects the input mode from the path if not specified.

    Args:
        input_path: Path to a MuleSoft project root directory or a single flow XML file.
        mode: Explicit input mode override. If None, auto-detected from the path.

    Returns:
        A ProjectInventory model with all discovered artifacts and any warnings.

    Raises:
        FileNotFoundError: If the input path does not exist.
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    if mode is None:
        mode = detect_input_mode(input_path)

    if mode == InputMode.SINGLE_FLOW:
        return parse_single_flow(input_path)
    else:
        return discover_project(input_path)
