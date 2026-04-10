"""Tests for mule2logic_agent.core.io."""

import tempfile
from pathlib import Path

import pytest

from mule2logic_agent.core.io import read_input


class TestReadInput:
    @pytest.mark.asyncio
    async def test_reads_valid_file(self):
        fixtures_dir = Path(__file__).parent / "fixtures"
        content = await read_input(str(fixtures_dir / "simple-flow.xml"))
        assert '<flow name="test">' in content
        assert '<http:listener path="/hello"/>' in content
        assert '<set-payload value="Hello"/>' in content

    @pytest.mark.asyncio
    async def test_raises_on_nonexistent_file(self):
        with pytest.raises(FileNotFoundError, match="File not found"):
            await read_input("/no/such/file.xml")

    @pytest.mark.asyncio
    async def test_raises_on_empty_input(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".xml", delete=False
        ) as f:
            f.write("   ")
            f.flush()
            with pytest.raises(ValueError, match="Input is empty"):
                await read_input(f.name)
        Path(f.name).unlink(missing_ok=True)
