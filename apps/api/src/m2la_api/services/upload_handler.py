"""Handle file uploads for the migration API.

Provides utilities to extract uploaded project zips and single-flow XML
files into temporary directories for pipeline processing.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import UploadFile

logger = logging.getLogger(__name__)


class UploadError(Exception):
    """Raised when an uploaded file cannot be processed."""


async def extract_project_upload(file: UploadFile) -> Path:
    """Extract an uploaded project zip into a temporary directory.

    Returns the path to the temporary directory root.  The caller is
    responsible for cleaning up via :func:`cleanup_upload`.

    Raises:
        UploadError: If the file is not a valid zip archive.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="m2la_upload_"))
    zip_path = tmp_dir / "upload.zip"

    try:
        content = await file.read()
        zip_path.write_bytes(content)

        if not zipfile.is_zipfile(zip_path):
            raise UploadError("Uploaded file is not a valid zip archive")

        extract_dir = tmp_dir / "project"
        extract_dir.mkdir()

        with zipfile.ZipFile(zip_path, "r") as zf:
            # Security: reject entries with absolute paths or path traversal
            for member in zf.namelist():
                member_path = Path(member)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise UploadError(f"Zip contains unsafe path: {member}")
                # Extra safety: verify resolved path stays within extract_dir
                resolved = (extract_dir / member).resolve()
                if not str(resolved).startswith(str(extract_dir.resolve())):
                    raise UploadError(f"Zip contains path that escapes extract directory: {member}")
            zf.extractall(extract_dir)

        zip_path.unlink()

        # If the zip contains a single top-level directory, use that as root
        top_entries = list(extract_dir.iterdir())
        if len(top_entries) == 1 and top_entries[0].is_dir():
            project_root = top_entries[0]
        else:
            project_root = extract_dir

        logger.info("Extracted project upload to %s", project_root)
        return project_root

    except UploadError:
        cleanup_upload(tmp_dir)
        raise
    except Exception as exc:
        cleanup_upload(tmp_dir)
        raise UploadError(f"Failed to extract upload: {exc}") from exc


async def save_single_flow_upload(file: UploadFile) -> Path:
    """Save an uploaded single-flow XML file into a temporary directory.

    Returns the path to the saved XML file.  The caller is responsible
    for cleaning up the parent directory via :func:`cleanup_upload`.

    Raises:
        UploadError: If the file cannot be read.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="m2la_upload_"))

    try:
        content = await file.read()
        filename = file.filename or "flow.xml"
        # Sanitize filename — use only the basename
        safe_name = Path(filename).name
        if not safe_name.lower().endswith(".xml"):
            safe_name = "flow.xml"

        flow_path = tmp_dir / safe_name
        flow_path.write_bytes(content)

        logger.info("Saved single-flow upload to %s", flow_path)
        return flow_path

    except Exception as exc:
        cleanup_upload(tmp_dir)
        raise UploadError(f"Failed to save upload: {exc}") from exc


def cleanup_upload(path: Path) -> None:
    """Remove a temporary upload directory and all its contents."""
    try:
        if path.exists():
            # Walk up to find the m2la_upload_ temp root
            cleanup_root = path
            while cleanup_root.parent != cleanup_root:
                if cleanup_root.name.startswith("m2la_upload_"):
                    break
                cleanup_root = cleanup_root.parent

            if cleanup_root.name.startswith("m2la_upload_"):
                shutil.rmtree(cleanup_root, ignore_errors=True)
                logger.debug("Cleaned up upload dir: %s", cleanup_root)
            else:
                # Safety: don't delete arbitrary paths
                logger.warning("Skipping cleanup for non-upload path: %s", path)
    except Exception:
        logger.exception("Failed to clean up upload directory: %s", path)
