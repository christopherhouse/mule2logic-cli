"""Tests for the public ``m2la_parser.parse`` entry-point."""

from pathlib import Path

import pytest
from m2la_contracts.enums import InputMode

from m2la_parser import parse


class TestAutoDetectProjectMode:
    """Verify auto-detection selects PROJECT mode for a directory."""

    def test_auto_detect_project_mode(self, hello_world_project: Path) -> None:
        inventory = parse(str(hello_world_project))
        assert inventory.mode == InputMode.PROJECT


class TestAutoDetectSingleFlowMode:
    """Verify auto-detection selects SINGLE_FLOW mode for an .xml file."""

    def test_auto_detect_single_flow_mode(self, standalone_flow_xml: Path) -> None:
        inventory = parse(str(standalone_flow_xml))
        assert inventory.mode == InputMode.SINGLE_FLOW


class TestExplicitModeOverride:
    """Verify that an explicit mode override is honoured."""

    def test_explicit_mode_override_single_flow_with_xml(self, standalone_flow_xml: Path) -> None:
        """Passing an explicit SINGLE_FLOW mode should be honoured."""
        inventory = parse(str(standalone_flow_xml), mode=InputMode.SINGLE_FLOW)
        assert inventory.mode == InputMode.SINGLE_FLOW

    def test_explicit_mode_override_project_with_dir(self, hello_world_project: Path) -> None:
        """Passing an explicit PROJECT mode should be honoured."""
        inventory = parse(str(hello_world_project), mode=InputMode.PROJECT)
        assert inventory.mode == InputMode.PROJECT

    def test_explicit_mode_override_dir_as_single_flow(self, hello_world_project: Path) -> None:
        """Passing SINGLE_FLOW for a directory path raises IsADirectoryError
        because ET.parse cannot open a directory as a file."""
        with pytest.raises(IsADirectoryError):
            parse(str(hello_world_project), mode=InputMode.SINGLE_FLOW)


class TestFileNotFound:
    """Verify FileNotFoundError for a non-existent path."""

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            parse("/tmp/this/path/does/not/exist")
