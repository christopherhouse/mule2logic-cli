"""Golden tests comparing generated Logic Apps artifacts against approved outputs.

These tests build IR fixtures that mirror the sample Mule projects in
packages/sample-projects/, run the transformer, and compare the output
against approved (checked-in) JSON files.

Includes:
- Project-mode golden test (hello-world-project equivalent)
- Single-flow-mode golden test (standalone-flow.xml equivalent)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from m2la_ir.builders import (
    build_project_ir,
    make_dataweave_transform,
    make_error_handler,
    make_flow,
    make_http_request,
    make_http_trigger,
    make_processor,
    make_scheduler_trigger,
    make_set_variable,
)
from m2la_ir.enums import (
    ErrorHandlerType,
    FlowKind,
    ProcessorType,
)

from m2la_transform.generator import generate_project
from m2la_transform.workflow_generator import generate_workflow

GOLDEN_DIR = Path(__file__).parent / "golden"


def _load_golden(name: str) -> dict[str, Any]:
    """Load a golden JSON file."""
    path = GOLDEN_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_json(data: Any) -> str:
    """Serialize to deterministic JSON for comparison."""
    return json.dumps(data, indent=2, sort_keys=True)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_hello_flow():
    """Build an IR flow equivalent to hello-flow.xml helloFlow."""
    return make_flow(
        name="helloFlow",
        kind=FlowKind.FLOW,
        trigger=make_http_trigger(path="/hello", method="GET"),
        steps=[
            make_set_variable(variable_name="greeting", value="${greeting.message}"),
            make_dataweave_transform(
                expression=(
                    "%dw 2.0\noutput application/json\n---\n{\n    message: vars.greeting,\n    timestamp: now()\n}"
                ),
            ),
            make_processor(
                ProcessorType.FLOW_REF,
                config={"flow_name": "sharedLogic"},
            ),
            make_http_request(method="POST", url="https://example.com/api"),
        ],
        error_handlers=[
            make_error_handler(
                handler_type=ErrorHandlerType.ON_ERROR_PROPAGATE,
                error_type="HTTP:CONNECTIVITY",
                steps=[
                    make_processor(
                        ProcessorType.SET_PAYLOAD,
                        config={"value": "Connection error occurred"},
                    ),
                ],
            ),
            make_error_handler(
                handler_type=ErrorHandlerType.ON_ERROR_CONTINUE,
                error_type="ANY",
                steps=[
                    make_processor(
                        ProcessorType.SET_PAYLOAD,
                        config={"value": "An error occurred"},
                    ),
                ],
            ),
        ],
    )


def _make_scheduled_flow():
    """Build an IR flow equivalent to scheduledFlow."""
    return make_flow(
        name="scheduledFlow",
        kind=FlowKind.FLOW,
        trigger=make_scheduler_trigger(frequency="60000", time_unit="MILLISECONDS"),
        steps=[
            make_processor(
                ProcessorType.SET_PAYLOAD,
                config={"value": "Scheduled task executed"},
            ),
        ],
    )


def _make_shared_logic_subflow():
    """Build an IR sub-flow equivalent to shared-subflow.xml sharedLogic."""
    return make_flow(
        name="sharedLogic",
        kind=FlowKind.SUB_FLOW,
        steps=[
            make_set_variable(variable_name="status", value="processed"),
            make_processor(
                ProcessorType.SET_PAYLOAD,
                config={"value": "Processed by shared logic"},
            ),
        ],
    )


def _make_standalone_flow():
    """Build IR for standalone-flow.xml (single-flow mode)."""
    return make_flow(
        name="standaloneApiFlow",
        kind=FlowKind.FLOW,
        trigger=make_http_trigger(path="/api/data", method="GET"),
        steps=[
            make_set_variable(variable_name="apiKey", value="${api.key}"),
            make_dataweave_transform(
                expression=("%dw 2.0\noutput application/json\n---\n{\n    data: payload,\n    key: vars.apiKey\n}"),
            ),
            make_processor(
                ProcessorType.FLOW_REF,
                config={"flow_name": "externalProcessingFlow"},
            ),
            make_http_request(method="GET", url="${backend.url}/items"),
        ],
        error_handlers=[
            make_error_handler(
                handler_type=ErrorHandlerType.ON_ERROR_PROPAGATE,
                error_type="HTTP:CONNECTIVITY",
                steps=[
                    make_processor(
                        ProcessorType.SET_PAYLOAD,
                        config={"value": "Connection failed"},
                    ),
                ],
            ),
        ],
    )


def _make_standalone_helper_subflow():
    """Build the localHelper sub-flow from standalone-flow.xml."""
    return make_flow(
        name="localHelper",
        kind=FlowKind.SUB_FLOW,
        steps=[
            make_set_variable(variable_name="processed", value="true"),
            make_processor(
                ProcessorType.SET_PAYLOAD,
                config={"value": "Processed locally"},
            ),
        ],
    )


# ── Golden test: single-flow mode ────────────────────────────────────────────


class TestGoldenSingleFlow:
    """Golden test for single-flow mode (standalone-flow.xml → workflow.json)."""

    def test_standalone_flow_matches_golden(self) -> None:
        """Generated workflow for standalone-flow.xml matches the approved golden file."""
        flow = _make_standalone_flow()
        local_helper = _make_standalone_helper_subflow()

        # In single-flow mode we have access to local sub-flows in the same file
        sub_flows = {"localHelper": local_helper}

        # externalProcessingFlow is NOT available → should produce a gap
        wf, gaps = generate_workflow(flow, sub_flows=sub_flows)

        golden = _load_golden("standalone_flow_workflow.json")
        assert _normalize_json(wf) == _normalize_json(golden), (
            f"Generated workflow does not match golden.\n"
            f"Generated:\n{_normalize_json(wf)}\n"
            f"Expected:\n{_normalize_json(golden)}"
        )

        # Verify expected gap for unresolved flow-ref
        assert any(g.construct_name == "flow_ref" for g in gaps)
        # Verify complex DataWeave gap
        assert any("dataweave" in g.construct_name for g in gaps)


# ── Golden test: project mode ─────────────────────────────────────────────────


class TestGoldenProject:
    """Golden test for project mode (hello-world-project equivalent)."""

    def test_hello_flow_workflow_matches_golden(self) -> None:
        """Generated helloFlow workflow matches the approved golden file."""
        hello = _make_hello_flow()
        shared = _make_shared_logic_subflow()

        wf, gaps = generate_workflow(hello, sub_flows={"sharedLogic": shared})

        golden = _load_golden("helloflow_workflow.json")
        assert _normalize_json(wf) == _normalize_json(golden), (
            f"Generated helloFlow workflow does not match golden.\n"
            f"Generated:\n{_normalize_json(wf)}\n"
            f"Expected:\n{_normalize_json(golden)}"
        )

    def test_scheduled_flow_workflow_matches_golden(self) -> None:
        """Generated scheduledFlow workflow matches the approved golden file."""
        scheduled = _make_scheduled_flow()

        wf, _ = generate_workflow(scheduled)

        golden = _load_golden("scheduledflow_workflow.json")
        assert _normalize_json(wf) == _normalize_json(golden), (
            f"Generated scheduledFlow workflow does not match golden.\n"
            f"Generated:\n{_normalize_json(wf)}\n"
            f"Expected:\n{_normalize_json(golden)}"
        )

    def test_project_generates_expected_files(self, tmp_path: Path) -> None:
        """Full project generation creates all expected files."""
        hello = _make_hello_flow()
        scheduled = _make_scheduled_flow()
        shared = _make_shared_logic_subflow()

        ir = build_project_ir(
            source_path="/projects/hello-world",
            project_name="hello-world",
            artifact_id="hello-world",
            version="1.0.0",
            flows=[hello, scheduled, shared],
        )

        artifacts, gaps = generate_project(ir, tmp_path)

        # Verify expected files
        assert (tmp_path / "host.json").exists()
        assert (tmp_path / "connections.json").exists()
        assert (tmp_path / "parameters.json").exists()
        assert (tmp_path / ".env").exists()

        # Verify workflow directories
        workflow_dirs = {d.name for d in (tmp_path / "workflows").iterdir()}
        assert "helloflow" in workflow_dirs
        assert "scheduledflow" in workflow_dirs
