"""Workflow graph route - returns state machine as nodes + edges for visualization."""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

_WORKFLOW_PATH = Path(__file__).resolve().parents[3] / "config" / "workflows.yaml"

# Agent-friendly display names
_STATE_LABELS: dict[str, str] = {
    "requirements_analysis": "Requirements Analysis",
    "architecture_design": "Architecture Design",
    "coding": "Coding",
    "testing": "Testing",
    "code_review": "Code Review",
    "revision": "Revision",
    "approved": "Approved",
}

# Manual layout positions (x, y) for a clean top-to-bottom flow
# The revision node is offset to the right for the feedback loop
_STATE_POSITIONS: dict[str, dict[str, int]] = {
    "requirements_analysis": {"x": 300, "y": 0},
    "architecture_design": {"x": 300, "y": 120},
    "coding": {"x": 300, "y": 240},
    "testing": {"x": 300, "y": 360},
    "code_review": {"x": 180, "y": 500},
    "revision": {"x": 480, "y": 500},
    "approved": {"x": 180, "y": 640},
}

_GUARD_LABELS: dict[str, str] = {
    "always": "",
    "tests_passed": "passed",
    "tests_failed": "failed",
    "review_approved": "approved",
    "review_revision_needed": "revise",
}


@router.get("/graph")
async def get_workflow_graph() -> dict:
    """Return workflow state machine as nodes and edges for frontend visualization."""
    with open(_WORKFLOW_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    nodes = []
    for state_def in raw["states"]:
        name = state_def["name"]
        nodes.append({
            "id": name,
            "label": _STATE_LABELS.get(name, name),
            "agent": state_def.get("agent"),
            "position": _STATE_POSITIONS.get(name, {"x": 300, "y": 0}),
        })

    edges = []
    for i, t in enumerate(raw["transitions"]):
        guard = t["guard"]
        edges.append({
            "id": f"e{i}",
            "source": t["from"],
            "target": t["to"],
            "guard": guard,
            "label": _GUARD_LABELS.get(guard, guard),
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "initial_state": raw.get("initial_state", "requirements_analysis"),
    }
