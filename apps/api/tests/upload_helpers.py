"""Test helpers for creating multipart upload payloads.

Provides utilities used by the API route tests to construct zip archives
and XML content for file-upload-based endpoints.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path


def make_project_zip(project_dir: str | Path) -> bytes:
    """Create an in-memory zip archive from a project directory.

    Returns the raw zip bytes suitable for multipart upload.
    """
    project_path = Path(project_dir)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(project_path.rglob("*")):
            if file_path.is_file():
                arcname = file_path.relative_to(project_path.parent)
                zf.write(file_path, arcname)
    return buf.getvalue()


def make_dummy_project_zip() -> bytes:
    """Create a minimal dummy Mule project zip for unit tests.

    Contains a pom.xml and a minimal flow XML, enough for mode detection.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("my-project/pom.xml", "<project><artifactId>test</artifactId></project>")
        zf.writestr(
            "my-project/src/main/mule/main.xml",
            '<?xml version="1.0"?>\n<mule><flow name="testFlow" /></mule>',
        )
    return buf.getvalue()


def make_single_flow_xml() -> bytes:
    """Return minimal Mule flow XML content for single-flow uploads."""
    return b'<?xml version="1.0"?>\n<mule><flow name="testFlow" /></mule>'
