"""Transition guard functions for the workflow state machine.

Each guard inspects the latest message to determine if a transition should fire.
"""

from __future__ import annotations


def always(message_content: str) -> bool:
    """Always returns True - unconditional transition."""
    return True


def tests_passed(message_content: str) -> bool:
    """Check if the tester reported all tests passed."""
    upper = message_content.upper()
    return "ALL TESTS PASSED" in upper


def tests_failed(message_content: str) -> bool:
    """Check if the tester reported test failures."""
    upper = message_content.upper()
    return "TESTS FAILED" in upper or "TEST FAILED" in upper


def review_approved(message_content: str) -> bool:
    """Check if the reviewer approved the code."""
    upper = message_content.upper()
    return "APPROVED" in upper and "REVISE" not in upper


def review_revision_needed(message_content: str) -> bool:
    """Check if the reviewer requested revisions."""
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
