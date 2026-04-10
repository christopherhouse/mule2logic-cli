"""Tests for the convert command — integration test with mocked agent."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from mule2logic_agent.models import ConvertResult
from mule2logic_cli.commands.convert import _convert_async

VALID_WORKFLOW = {
    "definition": {
        "triggers": {
            "manual": {
                "type": "Request",
                "kind": "Http",
                "inputs": {"method": "GET", "relativePath": "/hello"},
            }
        },
        "actions": {
            "Compose": {"type": "Compose", "inputs": "Hello", "runAfter": {}}
        },
    }
}

VALID_RESPONSE = json.dumps(VALID_WORKFLOW)


def _make_convert_result(**overrides):
    defaults = dict(
        workflow=VALID_WORKFLOW,
        raw_response=VALID_RESPONSE,
        explanation="",
        review_issues=[],
        report="",
    )
    defaults.update(overrides)
    return ConvertResult(**defaults)


class _FakeArgs:
    """Mimics the argparse Namespace."""

    def __init__(self, **kwargs):
        self.input = kwargs.get("input")
        self.output = kwargs.get("output")
        self.report = kwargs.get("report")
        self.explain = kwargs.get("explain", False)
        self.pretty = kwargs.get("pretty", False)
        self.verbose = kwargs.get("verbose", False)
        self.debug = kwargs.get("debug", False)
        self.model = kwargs.get("model", "gpt-4o")
        self.timeout = kwargs.get("timeout", 300.0)
        self.no_review = kwargs.get("no_review", False)


@pytest.mark.asyncio
class TestConvertCommand:
    @patch("mule2logic_cli.commands.convert.convert", new_callable=AsyncMock)
    async def test_converts_fixture_file(self, mock_convert, capsys):
        mock_convert.return_value = _make_convert_result()
        fixture = str(Path(__file__).parent / "fixtures" / "simple-flow.xml")
        args = _FakeArgs(input=fixture)
        await _convert_async(args)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["definition"]
        assert parsed["definition"]["triggers"]
        assert parsed["definition"]["actions"]

    @patch("mule2logic_cli.commands.convert.convert", new_callable=AsyncMock)
    async def test_pretty_prints(self, mock_convert, capsys):
        mock_convert.return_value = _make_convert_result()
        fixture = str(Path(__file__).parent / "fixtures" / "simple-flow.xml")
        args = _FakeArgs(input=fixture, pretty=True)
        await _convert_async(args)
        captured = capsys.readouterr()
        assert "\n" in captured.out
        parsed = json.loads(captured.out)
        assert parsed["definition"]

    @patch("mule2logic_cli.commands.convert.convert", new_callable=AsyncMock)
    async def test_explain_wraps_output(self, mock_convert, capsys):
        mock_convert.return_value = _make_convert_result(
            explanation="This is the explanation text."
        )
        fixture = str(Path(__file__).parent / "fixtures" / "simple-flow.xml")
        args = _FakeArgs(input=fixture, explain=True)
        await _convert_async(args)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "workflow" in parsed
        assert "explanation" in parsed
        assert parsed["explanation"] == "This is the explanation text."
        assert parsed["workflow"]["definition"]

    @patch("mule2logic_cli.commands.convert.convert", new_callable=AsyncMock)
    async def test_writes_to_file(self, mock_convert, tmp_path):
        mock_convert.return_value = _make_convert_result()
        fixture = str(Path(__file__).parent / "fixtures" / "simple-flow.xml")
        out_file = str(tmp_path / "output.json")
        args = _FakeArgs(input=fixture, output=out_file)
        await _convert_async(args)
        content = Path(out_file).read_text()
        parsed = json.loads(content)
        assert parsed["definition"]

    @patch("mule2logic_cli.commands.convert.convert", new_callable=AsyncMock)
    async def test_exits_on_missing_file(self, mock_convert):
        mock_convert.return_value = _make_convert_result()
        args = _FakeArgs(input="/no/such/file.xml")
        with pytest.raises(SystemExit) as exc_info:
            await _convert_async(args)
        assert exc_info.value.code == 1
