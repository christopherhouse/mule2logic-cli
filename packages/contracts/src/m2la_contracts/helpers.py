"""Helper utilities for contract handling."""

from m2la_contracts.enums import InputMode


def detect_input_mode(path: str) -> InputMode:
    """Detect input mode from the given path.

    Returns InputMode.SINGLE_FLOW if the path ends with '.xml',
    otherwise returns InputMode.PROJECT (assumed to be a directory).

    Args:
        path: File system path to a MuleSoft project directory or flow XML file.

    Returns:
        The detected InputMode.
    """
    if path.lower().endswith(".xml"):
        return InputMode.SINGLE_FLOW
    return InputMode.PROJECT
