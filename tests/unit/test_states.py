"""Tests for workflow states module."""

from src.orchestration.states import STATE_AGENT_MAP, WorkflowState


class TestWorkflowState:
    def test_all_states_exist(self) -> None:
        states = [s.value for s in WorkflowState]
        assert "requirements_analysis" in states
        assert "architecture_design" in states
        assert "coding" in states
        assert "testing" in states
        assert "code_review" in states
        assert "revision" in states
        assert "approved" in states

    def test_total_state_count(self) -> None:
        assert len(WorkflowState) == 7

    def test_string_enum(self) -> None:
        assert WorkflowState.CODING == "coding"
        assert str(WorkflowState.TESTING) == "WorkflowState.TESTING"


class TestStateAgentMap:
    def test_all_states_mapped(self) -> None:
        for state in WorkflowState:
            assert state in STATE_AGENT_MAP

    def test_agent_assignments(self) -> None:
        assert STATE_AGENT_MAP[WorkflowState.REQUIREMENTS_ANALYSIS] == "product_manager"
        assert STATE_AGENT_MAP[WorkflowState.ARCHITECTURE_DESIGN] == "architect"
        assert STATE_AGENT_MAP[WorkflowState.CODING] == "coder"
        assert STATE_AGENT_MAP[WorkflowState.TESTING] == "tester"
        assert STATE_AGENT_MAP[WorkflowState.CODE_REVIEW] == "reviewer"
        assert STATE_AGENT_MAP[WorkflowState.REVISION] == "coder"

    def test_approved_is_terminal(self) -> None:
        assert STATE_AGENT_MAP[WorkflowState.APPROVED] is None
