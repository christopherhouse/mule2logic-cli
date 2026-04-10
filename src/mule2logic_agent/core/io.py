"""I/O utilities — reads MuleSoft XML from files or stdin."""

from __future__ import annotations

import sys
from pathlib import Path


async def read_input(file_path: str | None = None) -> str:
    """Read MuleSoft XML from *file_path* or stdin.

    Raises ``ValueError`` when the resolved content is empty.
    Raises ``FileNotFoundError`` when *file_path* does not exist.
    """
    if file_path is not None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        content = path.read_text(encoding="utf-8")
    else:
        content = sys.stdin.read()

    if not content or not content.strip():
        raise ValueError("Input is empty")

    return content
