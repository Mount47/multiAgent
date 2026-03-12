"""Base utilities shared across agents."""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"


def load_system_prompt(role: str) -> str:
    """Load the system prompt for a given agent role from config/prompts/.

    Args:
        role: Agent role name (e.g., "coder", "tester").

    Returns:
        The system prompt text.
    """
    prompt_path = _PROMPTS_DIR / f"{role}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")
