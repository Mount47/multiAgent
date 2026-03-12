"""Workflow state definitions."""

from __future__ import annotations

from enum import Enum


class WorkflowState(str, Enum):
    """All possible states in the development workflow."""

    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    ARCHITECTURE_DESIGN = "architecture_design"
    CODING = "coding"
    TESTING = "testing"
    CODE_REVIEW = "code_review"
    REVISION = "revision"
    APPROVED = "approved"


# Map each state to its responsible agent role
STATE_AGENT_MAP: dict[WorkflowState, str | None] = {
    WorkflowState.REQUIREMENTS_ANALYSIS: "product_manager",
    WorkflowState.ARCHITECTURE_DESIGN: "architect",
    WorkflowState.CODING: "coder",
    WorkflowState.TESTING: "tester",
    WorkflowState.CODE_REVIEW: "reviewer",
    WorkflowState.REVISION: "coder",
    WorkflowState.APPROVED: None,  # Terminal state
}
