"""Tests for shared enumerations."""

from m2la_contracts.enums import ConstructCategory, GapCategory, InputMode, Severity


class TestInputMode:
    """Tests for InputMode enum."""

    def test_values(self) -> None:
        assert InputMode.PROJECT == "project"
        assert InputMode.SINGLE_FLOW == "single_flow"

    def test_is_str(self) -> None:
        assert isinstance(InputMode.PROJECT, str)

    def test_all_members(self) -> None:
        assert set(InputMode) == {InputMode.PROJECT, InputMode.SINGLE_FLOW}


class TestSeverity:
    """Tests for Severity enum."""

    def test_values(self) -> None:
        assert Severity.INFO == "info"
        assert Severity.WARNING == "warning"
        assert Severity.ERROR == "error"
        assert Severity.CRITICAL == "critical"

    def test_all_members(self) -> None:
        assert len(Severity) == 4


class TestGapCategory:
    """Tests for GapCategory enum."""

    def test_values(self) -> None:
        assert GapCategory.UNSUPPORTED_CONSTRUCT == "unsupported_construct"
        assert GapCategory.CONNECTOR_MISMATCH == "connector_mismatch"
        assert GapCategory.DATAWEAVE_COMPLEXITY == "dataweave_complexity"

    def test_all_members(self) -> None:
        assert len(GapCategory) == 5


class TestConstructCategory:
    """Tests for ConstructCategory enum."""

    def test_values(self) -> None:
        assert ConstructCategory.TRIGGER == "trigger"
        assert ConstructCategory.ROUTER == "router"
        assert ConstructCategory.CONNECTOR == "connector"
        assert ConstructCategory.ERROR_HANDLER == "error_handler"
        assert ConstructCategory.TRANSFORM == "transform"
        assert ConstructCategory.SCOPE == "scope"
        assert ConstructCategory.FLOW_CONTROL == "flow_control"

    def test_all_members(self) -> None:
        assert len(ConstructCategory) == 7
