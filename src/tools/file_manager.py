"""File management tool - read/write files in the workspace."""

from __future__ import annotations

from pathlib import Path

from config.settings import settings


def write_file(filename: str, content: str) -> str:
    """Write content to a file in the workspace directory.

    Args:
        filename: Name of the file (no path traversal allowed).
        content: File content to write.

    Returns:
        Success/error message.
    """
    # Prevent path traversal
    safe_name = Path(filename).name
    if safe_name != filename:
        return f"[ERROR] Invalid filename: {filename}. Use simple filenames only."

    workspace = Path(settings.workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)

    file_path = workspace / safe_name
    file_path.write_text(content, encoding="utf-8")
    return f"File written: {file_path}"


def read_file(filename: str) -> str:
    """Read content from a file in the workspace directory.

    Args:
        filename: Name of the file to read.

    Returns:
        File content or error message.
    """
    safe_name = Path(filename).name
    workspace = Path(settings.workspace_dir)
    file_path = workspace / safe_name

    if not file_path.exists():
        return f"[ERROR] File not found: {filename}"

    return file_path.read_text(encoding="utf-8")
