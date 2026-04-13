"""Tests for helper utilities."""

from m2la_contracts.enums import InputMode
from m2la_contracts.helpers import detect_input_mode


class TestDetectInputMode:
    """Tests for detect_input_mode helper."""

    def test_xml_file(self) -> None:
        assert detect_input_mode("flows/main.xml") == InputMode.SINGLE_FLOW

    def test_xml_uppercase(self) -> None:
        assert detect_input_mode("flows/MAIN.XML") == InputMode.SINGLE_FLOW

    def test_xml_mixed_case(self) -> None:
        assert detect_input_mode("flows/Main.Xml") == InputMode.SINGLE_FLOW

    def test_directory(self) -> None:
        assert detect_input_mode("/path/to/project") == InputMode.PROJECT

    def test_directory_trailing_slash(self) -> None:
        assert detect_input_mode("/path/to/project/") == InputMode.PROJECT

    def test_non_xml_file(self) -> None:
        assert detect_input_mode("config.json") == InputMode.PROJECT

    def test_empty_string(self) -> None:
        assert detect_input_mode("") == InputMode.PROJECT
