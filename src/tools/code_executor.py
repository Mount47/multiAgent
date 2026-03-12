"""Sandboxed code execution tool for agents."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from config.settings import settings


def execute_python_code(code: str) -> str:
    """Execute Python code in a subprocess and return the output.

    Args:
        code: Python source code to execute.

    Returns:
        stdout + stderr output from execution.
    """
    workspace = Path(settings.workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)

    # Write code to a temp file in workspace
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        dir=workspace,
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(code)
        temp_path = f.name

    try:
        result = subprocess.run(
            ["python", temp_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=workspace,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"
        return output.strip() or "[No output]"
    except subprocess.TimeoutExpired:
        return "[ERROR] Code execution timed out (30s limit)"
    except Exception as e:
        return f"[ERROR] Execution failed: {e}"
    finally:
        Path(temp_path).unlink(missing_ok=True)
