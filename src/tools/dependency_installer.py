"""Dependency installer tool - pip install in workspace."""

from __future__ import annotations

import subprocess


def install_dependency(package: str) -> str:
    """Install a Python package using pip.

    Args:
        package: Package name (e.g., "requests", "flask>=2.0").

    Returns:
        Installation output or error.
    """
    # Basic validation
    if not package or len(package) > 100:
        return "[ERROR] Invalid package name"

    # Block obviously dangerous inputs
    dangerous = [";", "&", "|", "`", "$", "(", ")", "{", "}"]
    if any(c in package for c in dangerous):
        return "[ERROR] Invalid characters in package name"

    try:
        result = subprocess.run(
            ["pip", "install", package],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout
        if result.returncode != 0:
            output += "\n[STDERR]\n" + result.stderr
        return output.strip()
    except subprocess.TimeoutExpired:
        return "[ERROR] Installation timed out (120s limit)"
    except Exception as e:
        return f"[ERROR] Installation failed: {e}"
