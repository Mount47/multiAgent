"""Tests for workflow state machine."""

import pytest

from src.orchestration.state_machine import WorkflowStateMachine
from src.orchestration.states import WorkflowState


@pytest.fixture
def sm() -> WorkflowStateMachine:
    """Load state machine from the real workflows.yaml."""
    return WorkflowStateMachine.from_yaml()


class TestStateMachineInit:
    def test_initial_state(self, sm: WorkflowStateMachine) -> None:
        assert sm.current_state == WorkflowState.REQUIREMENTS_ANALYSIS

    def test_not_complete_initially(self, sm: WorkflowStateMachine) -> None:
        assert sm.is_complete is False

    def test_transitions_loaded(self, sm: WorkflowStateMachine) -> None:
        assert len(sm.transitions) > 0

    def test_max_rounds_from_yaml(self, sm: WorkflowStateMachine) -> None:
        assert sm.max_rounds == 30

    def test_max_revisions_from_yaml(self, sm: WorkflowStateMachine) -> None:
        assert sm.max_revisions == 3


class TestStateMachineHappyPath:
    """Test the normal flow: requirements -> architecture -> coding -> testing -> review -> approved."""

    def test_requirements_to_architecture(self, sm: WorkflowStateMachine) -> None:
        agent = sm.advance("Requirements doc ready")
        assert sm.current_state == WorkflowState.ARCHITECTURE_DESIGN
        assert agent == "architect"

    def test_architecture_to_coding(self, sm: WorkflowStateMachine) -> None:
        sm.advance("Requirements doc ready")
        agent = sm.advance("Architecture designed")
        assert sm.current_state == WorkflowState.CODING
        assert agent == "coder"

    def test_coding_to_testing(self, sm: WorkflowStateMachine) -> None:
        sm.advance("Requirements doc ready")
        sm.advance("Architecture designed")
        agent = sm.advance("Code implemented")
        assert sm.current_state == WorkflowState.TESTING
        assert agent == "tester"

    def test_testing_passed_to_review(self, sm: WorkflowStateMachine) -> None:
        sm.advance("Requirements doc ready")
        sm.advance("Architecture designed")
        sm.advance("Code implemented")
        agent = sm.advance("ALL TESTS PASSED")
        assert sm.current_state == WorkflowState.CODE_REVIEW
        assert agent == "reviewer"

    def test_review_approved_completes(self, sm: WorkflowStateMachine) -> None:
        sm.advance("Requirements doc ready")
        sm.advance("Architecture designed")
        sm.advance("Code implemented")
        sm.advance("ALL TESTS PASSED")
        agent = sm.advance("Code looks good. APPROVED")
        assert sm.current_state == WorkflowState.APPROVED
        assert agent is None
        assert sm.is_complete is True


class TestStateMachineRevisionPath:
    """Test the revision loop."""

    def _advance_to_testing(self, sm: WorkflowStateMachine) -> None:
        sm.advance("Requirements ready")
        sm.advance("Architecture done")
        sm.advance("Code done")

    def test_tests_failed_goes_to_revision(self, sm: WorkflowStateMachine) -> None:
        self._advance_to_testing(sm)
        agent = sm.advance("TESTS FAILED: 2 errors")
        assert sm.current_state == WorkflowState.REVISION
        assert agent == "coder"

    def test_revision_goes_back_to_testing(self, sm: WorkflowStateMachine) -> None:
        self._advance_to_testing(sm)
        sm.advance("TESTS FAILED: 2 errors")
        agent = sm.advance("Fixed the code")
        assert sm.current_state == WorkflowState.TESTING
        assert agent == "tester"

    def test_review_revise_goes_to_revision(self, sm: WorkflowStateMachine) -> None:
        self._advance_to_testing(sm)
        sm.advance("ALL TESTS PASSED")
        agent = sm.advance("Please REVISE the error handling")
        assert sm.current_state == WorkflowState.REVISION
        assert agent == "coder"


class TestStateMachineLimits:
    def test_max_rounds_exceeded_forces_approval(self, sm: WorkflowStateMachine) -> None:
        sm.max_rounds = 2
        sm.advance("msg1")
        sm.advance("msg2")
        result = sm.advance("msg3")
        assert sm.current_state == WorkflowState.APPROVED
        assert result is None

    def test_max_revisions_exceeded_forces_approval(self, sm: WorkflowStateMachine) -> None:
        sm.max_revisions = 1
        # Get to testing
        sm.advance("req")
        sm.advance("arch")
        sm.advance("code")
        # First revision
        sm.advance("TESTS FAILED")
        sm.advance("fixed")  # revision -> testing
        # Second revision attempt exceeds limit
        sm.advance("TESTS FAILED")
        assert sm.current_state == WorkflowState.APPROVED

    def test_reset(self, sm: WorkflowStateMachine) -> None:
        sm.advance("msg")
        sm.advance("msg2")
        sm.reset()
        assert sm.current_state == WorkflowState.REQUIREMENTS_ANALYSIS
        assert sm._round_count == 0
        assert sm._revision_count == 0
