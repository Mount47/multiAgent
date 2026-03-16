"""Workflow execution tracer - tracks state transitions, tools, and token usage."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class StateTransitionRecord:
    """Record of a single state transition."""

    from_state: str
    to_state: str
    agent: str
    started_at: float
    ended_at: float
    duration_ms: float
    # Backward compatibility for frontend/api consumers that still read this field.
    estimated_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class ToolCallRecord:
    """Record of a single tool call."""

    tool_name: str
    inputs: str
    output: str
    duration_ms: float
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    traceback: str | None = None


@dataclass
class WorkflowTrace:
    """Complete trace of a workflow execution."""

    task_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    transitions: list[StateTransitionRecord] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    final_status: str = "running"

    @property
    def duration_ms(self) -> float:
        if self.ended_at is None:
            return 0.0
        return (self.ended_at - self.started_at).total_seconds() * 1000

    @property
    def state_count(self) -> int:
        return len(self.transitions)


class WorkflowTracer:
    """Traces workflow execution for observability."""

    def __init__(self) -> None:
        self._traces: dict[str, WorkflowTrace] = {}
        self._current_state_start: dict[str, float] = {}
        self._current_state_info: dict[str, tuple[str, str]] = {}  # task_id -> (state, agent)

    def start_workflow(self, task_id: str) -> None:
        self._traces[task_id] = WorkflowTrace(task_id=task_id)
        logger.info("[trace] workflow started: %s", task_id)

    def enter_state(self, task_id: str, state: str, agent: str) -> None:
        self._close_current_state(task_id)
        self._current_state_start[task_id] = time.monotonic()
        self._current_state_info[task_id] = (state, agent)
        logger.info("[trace] %s -> state=%s agent=%s", task_id[:8], state, agent)

    def exit_state(
        self,
        task_id: str,
        estimated_tokens: int | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        self._close_current_state(
            task_id,
            estimated_tokens=estimated_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def record_tool_call(
        self,
        task_id: str,
        tool_name: str,
        inputs: str,
        output: str,
        duration_ms: float,
        success: bool,
        error: str | None = None,
        traceback: str | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        trace = self._traces.get(task_id)
        if trace is None:
            return
        trace.tool_calls.append(
            ToolCallRecord(
                tool_name=tool_name,
                inputs=inputs,
                output=output,
                duration_ms=duration_ms,
                success=success,
                error=error,
                traceback=traceback,
                timestamp=timestamp or datetime.now(timezone.utc),
            )
        )

    def end_workflow(self, task_id: str, status: str = "completed") -> WorkflowTrace | None:
        self._close_current_state(task_id)
        trace = self._traces.get(task_id)
        if trace:
            trace.ended_at = datetime.now(timezone.utc)
            trace.final_status = status
            trace.total_prompt_tokens = sum(t.prompt_tokens for t in trace.transitions)
            trace.total_completion_tokens = sum(t.completion_tokens for t in trace.transitions)
            trace.total_tokens = trace.total_prompt_tokens + trace.total_completion_tokens
            logger.info(
                "[trace] workflow ended: %s status=%s states=%d tokens=%d tools=%d duration=%.0fms",
                task_id[:8],
                status,
                trace.state_count,
                trace.total_tokens,
                len(trace.tool_calls),
                trace.duration_ms,
            )
        return trace

    def get_trace(self, task_id: str) -> WorkflowTrace | None:
        return self._traces.get(task_id)

    def list_traces(self) -> list[WorkflowTrace]:
        return list(self._traces.values())

    def _close_current_state(
        self,
        task_id: str,
        estimated_tokens: int | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        start = self._current_state_start.pop(task_id, None)
        info = self._current_state_info.pop(task_id, None)
        if start is None or info is None:
            return
        ended = time.monotonic()
        from_state, agent = info

        if estimated_tokens is None:
            estimated_tokens = prompt_tokens + completion_tokens
        elif prompt_tokens == 0 and completion_tokens == 0:
            # Backward compatible path: only total tokens available.
            prompt_tokens = estimated_tokens

        record = StateTransitionRecord(
            from_state=from_state,
            to_state="",  # filled on next enter or end
            agent=agent,
            started_at=start,
            ended_at=ended,
            duration_ms=(ended - start) * 1000,
            estimated_tokens=estimated_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        trace = self._traces.get(task_id)
        if trace:
            if trace.transitions:
                trace.transitions[-1].to_state = from_state
            trace.transitions.append(record)
