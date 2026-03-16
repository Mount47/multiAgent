"""Pre-flight health checks for CLI and API startup."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str


@dataclass
class HealthReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def critical_ok(self) -> bool:
        """At minimum workspace and python must work."""
        names = {c.name for c in self.checks if c.ok}
        return "workspace_writable" in names and "python_available" in names

    def summary(self) -> str:
        lines = []
        for c in self.checks:
            icon = "OK" if c.ok else "FAIL"
            lines.append(f"  [{icon}] {c.name}: {c.message}")
        return "\n".join(lines)


def check_workspace() -> CheckResult:
    """Check workspace directory exists and is writable."""
    workspace = Path(settings.workspace_dir)
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        test_file = workspace / ".healthcheck"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        return CheckResult("workspace_writable", True, str(workspace.resolve()))
    except Exception as e:
        return CheckResult("workspace_writable", False, str(e))


def check_python() -> CheckResult:
    """Check python executable is available."""
    python = shutil.which("python") or shutil.which("python3")
    if python:
        return CheckResult("python_available", True, python)
    return CheckResult("python_available", False, "python not found in PATH")


def check_pip() -> CheckResult:
    """Check pip is available."""
    pip = shutil.which("pip") or shutil.which("pip3")
    if pip:
        return CheckResult("pip_available", True, pip)
    return CheckResult("pip_available", False, "pip not found in PATH")


def check_pytest() -> CheckResult:
    """Check pytest is available."""
    pytest = shutil.which("pytest")
    if pytest:
        return CheckResult("pytest_available", True, pytest)
    return CheckResult("pytest_available", False, "pytest not found in PATH (tests may fail)")


def check_llm_api_key() -> CheckResult:
    """Check at least one LLM API key is configured."""
    default_model = os.environ.get("DEFAULT_MODEL", settings.default_model)

    # Ollama doesn't need an API key
    if "ollama" in default_model.lower():
        return CheckResult("llm_api_key", True, f"Using local Ollama ({default_model})")

    key_vars = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }

    # Check the default model's key first
    for name, env_var in key_vars.items():
        if name in default_model.lower():
            val = os.environ.get(env_var, "")
            if val:
                return CheckResult("llm_api_key", True, f"{env_var} is set (model: {default_model})")
            return CheckResult("llm_api_key", False, f"{env_var} not set for model {default_model}")

    # Check if any key exists
    for env_var in key_vars.values():
        if os.environ.get(env_var, ""):
            return CheckResult("llm_api_key", True, f"{env_var} is set")

    return CheckResult("llm_api_key", False, "No LLM API key found in environment")


async def check_llm_reachability() -> CheckResult:
    """Try to reach the LLM API with a minimal request."""
    try:
        from src.models.factory import ModelClientFactory
        factory = ModelClientFactory()
        default_model = os.environ.get("DEFAULT_MODEL", settings.default_model)
        client = factory.get_client(default_model)

        from autogen_core.models import UserMessage
        result = await client.create([UserMessage(content="Say OK", source="health")])
        if result and result.content:
            return CheckResult("llm_reachable", True, f"LLM responded ({default_model})")
        return CheckResult("llm_reachable", False, "LLM returned empty response")
    except Exception as e:
        msg = str(e)
        if len(msg) > 120:
            msg = msg[:120] + "..."
        return CheckResult("llm_reachable", False, msg)


def run_sync_checks() -> HealthReport:
    """Run all synchronous health checks."""
    report = HealthReport()
    report.checks.append(check_workspace())
    report.checks.append(check_python())
    report.checks.append(check_pip())
    report.checks.append(check_pytest())
    report.checks.append(check_llm_api_key())
    return report


async def run_all_checks(include_llm_ping: bool = False) -> HealthReport:
    """Run all health checks including optional async LLM ping."""
    report = run_sync_checks()
    if include_llm_ping:
        report.checks.append(await check_llm_reachability())
    return report
