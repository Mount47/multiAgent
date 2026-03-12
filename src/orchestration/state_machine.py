"""Workflow state machine that drives agent orchestration.

Loaded from config/workflows.yaml. Determines which agent speaks next
based on the current state and the content of the latest message.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from src.orchestration.states import STATE_AGENT_MAP, WorkflowState
from src.orchestration.transitions import GUARD_REGISTRY

logger = logging.getLogger(__name__)

_WORKFLOW_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "workflows.yaml"


@dataclass
class Transition:
    """A state transition with a guard condition."""

    from_state: WorkflowState
    to_state: WorkflowState
    guard: Callable[[str], bool]
    guard_name: str  # For logging


@dataclass
class WorkflowStateMachine:
    """Finite state machine for the development workflow.

    Maintains current state and a transition table. On each agent message,
    `advance()` evaluates guards to determine the next state and returns
    the name of the next agent.
    """

    current_state: WorkflowState
    transitions: list[Transition]
    max_rounds: int = 30
    max_revisions: int = 3
    _round_count: int = field(default=0, repr=False)
    _revision_count: int = field(default=0, repr=False)

    @classmethod
    def from_yaml(cls, config_path: Path = _WORKFLOW_CONFIG_PATH) -> WorkflowStateMachine:
        """Load state machine from workflows.yaml."""
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        initial = WorkflowState(raw["initial_state"])

        transitions = []
        for t in raw["transitions"]:
            guard_name = t["guard"]
            guard_func = GUARD_REGISTRY.get(guard_name)
            if guard_func is None:
                raise ValueError(f"Unknown guard function: {guard_name}")

            transitions.append(
                Transition(
                    from_state=WorkflowState(t["from"]),
                    to_state=WorkflowState(t["to"]),
                    guard=guard_func,
                    guard_name=guard_name,
                )
            )

        return cls(
            current_state=initial,
            transitions=transitions,
            max_rounds=raw.get("max_rounds", 30),
            max_revisions=raw.get("max_revisions", 3),
        )

    def advance(self, message_content: str) -> str | None:
        """Evaluate transitions and advance to the next state.

        Returns:
            The name of the next agent, or None if workflow is complete.
        """
        self._round_count += 1

        if self._round_count > self.max_rounds:
            logger.warning("Max rounds (%d) exceeded, forcing approval", self.max_rounds)
            self.current_state = WorkflowState.APPROVED
            return None

        # Find matching transition
        for transition in self.transitions:
            if transition.from_state != self.current_state:
                continue

            if transition.guard(message_content):
                old_state = self.current_state
                self.current_state = transition.to_state

                # Track revision count
                if self.current_state == WorkflowState.REVISION:
                    self._revision_count += 1
                    if self._revision_count > self.max_revisions:
                        logger.warning(
                            "Max revisions (%d) exceeded, forcing approval",
                            self.max_revisions,
                        )
                        self.current_state = WorkflowState.APPROVED
                        return None

                logger.info(
                    "State transition: %s -> %s (guard: %s)",
                    old_state.value,
                    self.current_state.value,
                    transition.guard_name,
                )

                return STATE_AGENT_MAP.get(self.current_state)

        logger.warning(
            "No matching transition from state %s, staying in current state",
            self.current_state.value,
        )
        return STATE_AGENT_MAP.get(self.current_state)

    @property
    def is_complete(self) -> bool:
        """Check if the workflow has reached a terminal state."""
        return self.current_state == WorkflowState.APPROVED

    def reset(self) -> None:
        """Reset the state machine to initial state."""
        self.current_state = WorkflowState.REQUIREMENTS_ANALYSIS
        self._round_count = 0
        self._revision_count = 0
