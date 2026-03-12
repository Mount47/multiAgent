"""Test runner tool - executes pytest and returns results."""

from __future__ import annotations

import subprocess
from pathlib import Path

from config.settings import settings


def run_tests(test_code: str, source_code: str = "") -> str:
    """Write test code to file, execute with pytest, return results.

    Args:
        test_code: The pytest test code to execute.
        source_code: Optional source code to save alongside tests.

    Returns:
        Pytest output with pass/fail results.
    """
    workspace = Path(settings.workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)

    # Write source code if provided
    if source_code:
        source_path = workspace / "solution.py"
        source_path.write_text(source_code, encoding="utf-8")

    # Write test file
    test_path = workspace / "test_solution.py"
    test_path.write_text(test_code, encoding="utf-8")

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", str(test_path), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=workspace,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        return output.strip()
    except subprocess.TimeoutExpired:
        return "[ERROR] Test execution timed out (60s limit)"
    except Exception as e:
        return f"[ERROR] Test execution failed: {e}"
