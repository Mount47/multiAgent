"""Workspace file listing route for code result display."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from config.settings import settings

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


@router.get("/files")
async def list_workspace_files() -> list[dict]:
    """List all files in the workspace directory with their contents."""
    workspace = Path(settings.workspace_dir)
    if not workspace.exists():
        return []
    files = []
    for f in sorted(workspace.iterdir()):
        if f.is_file():
            try:
                content = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                content = "(binary or unreadable file)"
            files.append({"name": f.name, "content": content})
    return files
