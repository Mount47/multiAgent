"""Integration tests for the workflow state machine and guard functions.

Tests the full workflow path with simulated agent messages —
no real LLM calls, no AutoGen dependency.
"""

from __future__ import annotations

import pytest

from src.orchestration.state_machine import WorkflowStateMachine
from src.orchestration.states import WorkflowState
from src.orchestration.transitions import (
    _extract_json_verdict,
    review_approved,
    review_revision_needed,
    tests_failed as guard_tests_failed,
    tests_passed as guard_tests_passed,
)


# ---------------------------------------------------------------------------
# JSON verdict extraction
# ---------------------------------------------------------------------------

class TestJsonVerdictExtraction:
    """Test the JSON verdict parsing used by guards."""

    def test_fenced_json_block(self):
        msg = 'Some review text\n```json\n{"verdict": "APPROVED"}\n```'
        result = _extract_json_verdict(msg)
        assert result == {"verdict": "APPROVED"}

    def test_bare_json(self):
        msg = 'All good.\n{"verdict": "REVISE", "issues": ["bug"]}'
        result = _extract_json_verdict(msg)
        assert result == {"verdict": "REVISE", "issues": ["bug"]}

    def test_no_json(self):
        msg = "Just plain text with APPROVED keyword"
        result = _extract_json_verdict(msg)
        assert result is None

    def test_malformed_json(self):
        msg = '```json\n{"verdict": BROKEN}\n```'
        result = _extract_json_verdict(msg)
        assert result is None

    def test_json_with_extra_fields(self):
        msg = '```json\n{"verdict": "PASSED", "tests_run": 5, "tests_failed": 0}\n```'
        result = _extract_json_verdict(msg)
        assert result["verdict"] == "PASSED"
        assert result["tests_run"] == 5


# ---------------------------------------------------------------------------
# Guard functions with JSON verdicts
# ---------------------------------------------------------------------------

class TestGuardsWithJson:
    """Test that guards correctly parse JSON verdicts."""

    def test_tests_passed_json(self):
        msg = 'Tests done.\n```json\n{"verdict": "PASSED"}\n```'
        assert guard_tests_passed(msg) is True
        assert guard_tests_failed(msg) is False

    def test_tests_failed_json(self):
        msg = 'Tests done.\n```json\n{"verdict": "FAILED", "tests_run": 5, "tests_failed": 2}\n```'
        assert guard_tests_failed(msg) is True
        assert guard_tests_passed(msg) is False

    def test_review_approved_json(self):
        msg = 'Good code.\n```json\n{"verdict": "APPROVED"}\n```'
        assert review_approved(msg) is True
        assert review_revision_needed(msg) is False

    def test_review_revise_json(self):
        msg = 'Issues found.\n```json\n{"verdict": "REVISE", "issues": ["fix X"]}\n```'
        assert review_revision_needed(msg) is True
        assert review_approved(msg) is False


class TestGuardsKeywordFallback:
    """Test that guards still work with keyword matching (backward compat)."""

    def test_tests_passed_keyword(self):
        assert guard_tests_passed("ALL TESTS PASSED, 5/5 green") is True

    def test_tests_failed_keyword(self):
        assert guard_tests_failed("TESTS FAILED: 2 errors found") is True

    def test_review_approved_keyword(self):
        assert review_approved("Overall good. APPROVED") is True

    def test_review_revise_keyword(self):
        assert review_revision_needed("Please REVISE the error handling") is True

    def test_approved_not_triggered_by_revise(self):
        # "APPROVED" appears but "REVISE" also appears — should NOT match approved
        assert review_approved("Not APPROVED, please REVISE") is False


# ---------------------------------------------------------------------------
# Full workflow: happy path
# ---------------------------------------------------------------------------

class TestWorkflowHappyPath:
    """Test the full workflow: PM → Architect → Coder → Tester (pass) → Reviewer (approve)."""

    def test_happy_path_keyword(self):
        sm = WorkflowStateMachine.from_yaml()
        assert sm.current_state == WorkflowState.REQUIREMENTS_ANALYSIS

        # PM → Architect (always)
        next_agent = sm.advance("Here are the requirements: ...")
        assert sm.current_state == WorkflowState.ARCHITECTURE_DESIGN
        assert next_agent == "architect"

        # Architect → Coder (always)
        next_agent = sm.advance("System design: use module pattern...")
        assert sm.current_state == WorkflowState.CODING
        assert next_agent == "coder"

        # Coder → Tester (always)
        next_agent = sm.advance("def add(a, b): return a + b")
        assert sm.current_state == WorkflowState.TESTING
        assert next_agent == "tester"

        # Tester → Reviewer (tests_passed)
        next_agent = sm.advance("Ran 5 tests. ALL TESTS PASSED")
        assert sm.current_state == WorkflowState.CODE_REVIEW
        assert next_agent == "reviewer"

        # Reviewer → Approved (review_approved)
        next_agent = sm.advance("Code quality is good. APPROVED")
        assert sm.current_state == WorkflowState.APPROVED
        assert next_agent is None
        assert sm.is_complete

    def test_happy_path_json_verdicts(self):
        sm = WorkflowStateMachine.from_yaml()

        sm.advance("Requirements...")           # PM → Architect
        sm.advance("Architecture...")            # Architect → Coder
        sm.advance("Code implementation...")     # Coder → Tester

        # Tester with JSON verdict
        next_agent = sm.advance(
            'All tests green.\n```json\n{"verdict": "PASSED", "tests_run": 5, "tests_failed": 0}\n```'
        )
        assert sm.current_state == WorkflowState.CODE_REVIEW
        assert next_agent == "reviewer"

        # Reviewer with JSON verdict
        next_agent = sm.advance(
            'Looks great.\n```json\n{"verdict": "APPROVED"}\n```'
        )
        assert sm.current_state == WorkflowState.APPROVED
        assert sm.is_complete


# ---------------------------------------------------------------------------
# Full workflow: revision path
# ---------------------------------------------------------------------------

class TestWorkflowRevisionPath:
    """Test revision cycles: Tester fails → Coder revises → Tester passes → Reviewer approves."""

    def test_tester_fails_triggers_revision(self):
        sm = WorkflowStateMachine.from_yaml()

        sm.advance("Requirements...")    # PM → Architect
        sm.advance("Architecture...")    # Architect → Coder
        sm.advance("Code...")            # Coder → Tester

        # Tester fails
        next_agent = sm.advance("2 tests failed. TESTS FAILED")
        assert sm.current_state == WorkflowState.REVISION
        assert next_agent == "coder"

        # Coder revises → back to Tester
        next_agent = sm.advance("Fixed the bug, here's the new code")
        assert sm.current_state == WorkflowState.TESTING
        assert next_agent == "tester"

        # Tester passes this time
        next_agent = sm.advance("ALL TESTS PASSED")
        assert sm.current_state == WorkflowState.CODE_REVIEW
        assert next_agent == "reviewer"

        # Reviewer approves
        next_agent = sm.advance("APPROVED")
        assert sm.current_state == WorkflowState.APPROVED

    def test_reviewer_revise_triggers_revision(self):
        sm = WorkflowStateMachine.from_yaml()

        sm.advance("Requirements...")
        sm.advance("Architecture...")
        sm.advance("Code...")
        sm.advance("ALL TESTS PASSED")

        # Reviewer requests revision
        next_agent = sm.advance("Please REVISE: missing error handling")
        assert sm.current_state == WorkflowState.REVISION
        assert next_agent == "coder"

    def test_max_revisions_forces_approval(self):
        sm = WorkflowStateMachine.from_yaml()
        assert sm.max_revisions == 3

        sm.advance("Requirements...")
        sm.advance("Architecture...")
        sm.advance("Code...")

        # 3 revision cycles (test fail → revision → test fail → ...)
        for i in range(sm.max_revisions):
            sm.advance("TESTS FAILED")   # → revision
            sm.advance("Fixed code...")   # → testing

        # 4th failure should force approval
        next_agent = sm.advance("TESTS FAILED")
        # The state machine either forces approval or stays — depends on revision count
        # revision count increments when entering REVISION state
        # After 3 revisions, the 4th attempt to enter REVISION forces APPROVED
        assert sm.current_state == WorkflowState.APPROVED

    def test_max_rounds_forces_approval(self):
        sm = WorkflowStateMachine.from_yaml()
        sm._round_count = sm.max_rounds  # simulate reaching the limit

        next_agent = sm.advance("any message")
        assert sm.current_state == WorkflowState.APPROVED
        assert next_agent is None


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------

class TestHealthChecks:
    """Test the health check module."""

    def test_sync_checks_run(self):
        from src.health import run_sync_checks
        report = run_sync_checks()
        assert len(report.checks) == 5
        # At minimum workspace and python should pass in test env
        workspace_check = next(c for c in report.checks if c.name == "workspace_writable")
        python_check = next(c for c in report.checks if c.name == "python_available")
        assert workspace_check.ok
        assert python_check.ok
        assert report.critical_ok

    def test_report_summary_format(self):
        from src.health import run_sync_checks
        report = run_sync_checks()
        summary = report.summary()
        assert "[OK]" in summary or "[FAIL]" in summary


# ---------------------------------------------------------------------------
# Tool degradation
# ---------------------------------------------------------------------------

class TestToolDegradation:
    """Test that AgentFactory detects tool capability correctly."""

    def test_supports_tools_returns_bool(self):
        from src.agents.factory import AgentFactory
        from src.models.factory import ModelClientFactory

        factory_model = ModelClientFactory()
        agent_factory = AgentFactory(factory_model)

        # _supports_tools should return a bool without crashing
        result = agent_factory._supports_tools("coder")
        assert isinstance(result, bool)

        # Non-tool roles always return False
        assert agent_factory._supports_tools("product_manager") is False
        assert agent_factory._supports_tools("reviewer") is False
