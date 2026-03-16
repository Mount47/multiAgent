"""Transition guard functions for the workflow state machine.

Each guard inspects the latest message to determine if a transition should fire.
Supports JSON structured verdict with keyword-matching fallback.
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)


def _extract_json_verdict(message_content: str) -> dict | None:
    """Try to extract a JSON verdict block from message content.

    Looks for patterns like:
        ```json\n{"verdict": "APPROVED"}\n```
    or bare JSON:
        {"verdict": "APPROVED"}
    """
    # Try fenced code block first
    fenced = re.search(
        r"```(?:json)?\s*\n?\s*(\{.*?\})\s*\n?\s*```", message_content, re.DOTALL
    )
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # Try bare JSON object containing "verdict"
    bare = re.search(r'\{\s*"verdict"\s*:.*?\}', message_content, re.DOTALL)
    if bare:
        try:
            return json.loads(bare.group(0))
        except json.JSONDecodeError:
            pass

    return None


def always(message_content: str) -> bool:
    """Always returns True - unconditional transition."""
    return True


def tests_passed(message_content: str) -> bool:
    """Check if the tester reported all tests passed."""
    verdict = _extract_json_verdict(message_content)
    if verdict and "verdict" in verdict:
        v = verdict["verdict"].upper()
        if v in ("PASSED", "ALL_TESTS_PASSED", "ALL TESTS PASSED"):
            logger.info("Guard tests_passed: matched via JSON verdict")
            return True
        return False

    # Fallback: keyword matching
    upper = message_content.upper()
    return "ALL TESTS PASSED" in upper


def tests_failed(message_content: str) -> bool:
    """Check if the tester reported test failures."""
    verdict = _extract_json_verdict(message_content)
    if verdict and "verdict" in verdict:
        v = verdict["verdict"].upper()
        if v in ("FAILED", "TESTS_FAILED", "TESTS FAILED"):
            logger.info("Guard tests_failed: matched via JSON verdict")
            return True
        return False

    # Fallback: keyword matching
    upper = message_content.upper()
    return "TESTS FAILED" in upper or "TEST FAILED" in upper


def review_approved(message_content: str) -> bool:
    """Check if the reviewer approved the code."""
    verdict = _extract_json_verdict(message_content)
    if verdict and "verdict" in verdict:
        v = verdict["verdict"].upper()
        if v == "APPROVED":
            logger.info("Guard review_approved: matched via JSON verdict")
            return True
        return False

    # Fallback: keyword matching
    upper = message_content.upper()
    return "APPROVED" in upper and "REVISE" not in upper


def review_revision_needed(message_content: str) -> bool:
    """Check if the reviewer requested revisions."""
    verdict = _extract_json_verdict(message_content)
    if verdict and "verdict" in verdict:
        v = verdict["verdict"].upper()
        if v in ("REVISE", "REVISION_NEEDED"):
            logger.info("Guard review_revision_needed: matched via JSON verdict")
            return True
        return False

    # Fallback: keyword matching
    upper = message_content.upper()
    return "REVISE" in upper


# Registry: maps guard names (from workflows.yaml) to functions
GUARD_REGISTRY: dict[str, callable] = {
    "always": always,
    "tests_passed": tests_passed,
    "tests_failed": tests_failed,
    "review_approved": review_approved,
    "review_revision_needed": review_revision_needed,
}
