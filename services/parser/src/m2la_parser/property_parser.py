"""Parse Java .properties files from MuleSoft projects."""

from pathlib import Path

from m2la_contracts.common import Warning
from m2la_contracts.enums import Severity

from m2la_parser.models import PropertyFile


def parse_properties_file(file_path: Path, relative_to: Path | None = None) -> tuple[PropertyFile, list[Warning]]:
    """Parse a Java .properties file.

    Handles standard key=value and key:value formats, comments (#, !),
    and blank lines.

    Args:
        file_path: Absolute path to the properties file.
        relative_to: Base path for computing the relative file path.

    Returns:
        Tuple of (PropertyFile model, list of warnings).
    """
    warnings: list[Warning] = []
    base = relative_to or file_path.parent
    rel_path = str(file_path.relative_to(base)) if file_path.is_relative_to(base) else str(file_path)

    if not file_path.exists():
        warnings.append(
            Warning(
                code="MISSING_PROPERTY_FILE",
                message=f"Properties file not found: {rel_path}",
                severity=Severity.WARNING,
                source_location=rel_path,
            )
        )
        return PropertyFile(file_path=rel_path, properties={}), warnings

    properties: dict[str, str] = {}

    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        warnings.append(
            Warning(
                code="UNREADABLE_PROPERTY_FILE",
                message=f"Failed to read properties file: {e}",
                severity=Severity.WARNING,
                source_location=rel_path,
            )
        )
        return PropertyFile(file_path=rel_path, properties={}), warnings

    for line_num, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue

        # Split on first = or :
        for sep in ("=", ":"):
            if sep in stripped:
                key, value = stripped.split(sep, 1)
                properties[key.strip()] = value.strip()
                break
        else:
            # Line without separator — treat as key with empty value
            warnings.append(
                Warning(
                    code="MALFORMED_PROPERTY_LINE",
                    message=f"Line {line_num} has no separator: '{stripped}'",
                    severity=Severity.INFO,
                    source_location=f"{rel_path}:{line_num}",
                )
            )

    return PropertyFile(file_path=rel_path, properties=properties), warnings
