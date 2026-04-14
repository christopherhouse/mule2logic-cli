"""Public parse entry point for the MuleSoft parser."""

from pathlib import Path

from m2la_contracts.enums import InputMode
from m2la_contracts.helpers import detect_input_mode
from opentelemetry import metrics, trace

from m2la_parser.models import ProjectInventory
from m2la_parser.project_discovery import discover_project
from m2la_parser.single_flow import parse_single_flow

_tracer = trace.get_tracer("m2la.parser")
_meter = metrics.get_meter("m2la.parser")
_flows_parsed = _meter.create_counter("m2la.parser.flows_parsed", description="Total flows parsed", unit="1")
_constructs_parsed = _meter.create_counter(
    "m2la.parser.constructs_parsed", description="Total constructs parsed", unit="1"
)
_parser_warnings = _meter.create_counter("m2la.parser.warnings", description="Parser warnings emitted", unit="1")


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
    with _tracer.start_as_current_span("m2la.parser.parse") as span:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {input_path}")

        if mode is None:
            mode = detect_input_mode(input_path)

        span.set_attribute("input.mode", mode.value)
        span.set_attribute("input.path", input_path)

        if mode == InputMode.SINGLE_FLOW:
            result = parse_single_flow(input_path)
        else:
            result = discover_project(input_path)

        flow_count = len(result.flows)
        construct_count = sum(len(f.processors) for f in result.flows)
        warning_count = len(result.warnings)

        span.set_attribute("flows.count", flow_count)
        span.set_attribute("constructs.count", construct_count)
        span.set_attribute("warnings.count", warning_count)

        _flows_parsed.add(flow_count, {"mode": mode.value})
        _constructs_parsed.add(construct_count)
        _parser_warnings.add(warning_count)

        return result
