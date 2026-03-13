"""Simple in-memory metrics collector for workflow observability."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricsSummary:
    """Snapshot of collected metrics."""
    total_workflows: int = 0
    completed_workflows: int = 0
    failed_workflows: int = 0
    avg_duration_ms: float = 0.0
    total_state_transitions: int = 0
    total_estimated_tokens: int = 0
    agent_call_counts: dict[str, int] = field(default_factory=dict)
    state_avg_duration_ms: dict[str, float] = field(default_factory=dict)


class MetricsCollector:
    """Collects and aggregates workflow metrics."""

    def __init__(self) -> None:
        self._workflow_count = 0
        self._completed = 0
        self._failed = 0
        self._durations: list[float] = []
        self._state_transitions = 0
        self._total_tokens = 0
        self._agent_calls: dict[str, int] = defaultdict(int)
        self._state_durations: dict[str, list[float]] = defaultdict(list)
        self._start_time = time.monotonic()

    def record_workflow_start(self) -> None:
        self._workflow_count += 1

    def record_workflow_end(self, status: str, duration_ms: float) -> None:
        if status == "completed":
            self._completed += 1
        else:
            self._failed += 1
        self._durations.append(duration_ms)

    def record_state_transition(
        self, state: str, agent: str, duration_ms: float, tokens: int = 0
    ) -> None:
        self._state_transitions += 1
        self._total_tokens += tokens
        self._agent_calls[agent] += 1
        self._state_durations[state].append(duration_ms)

    def get_summary(self) -> MetricsSummary:
        avg_dur = sum(self._durations) / len(self._durations) if self._durations else 0.0
        state_avg: dict[str, float] = {}
        for state, durs in self._state_durations.items():
            state_avg[state] = sum(durs) / len(durs) if durs else 0.0

        return MetricsSummary(
            total_workflows=self._workflow_count,
            completed_workflows=self._completed,
            failed_workflows=self._failed,
            avg_duration_ms=avg_dur,
            total_state_transitions=self._state_transitions,
            total_estimated_tokens=self._total_tokens,
            agent_call_counts=dict(self._agent_calls),
            state_avg_duration_ms=state_avg,
        )

    def to_dict(self) -> dict:
        s = self.get_summary()
        return {
            "total_workflows": s.total_workflows,
            "completed_workflows": s.completed_workflows,
            "failed_workflows": s.failed_workflows,
            "avg_duration_ms": round(s.avg_duration_ms, 1),
            "total_state_transitions": s.total_state_transitions,
            "total_estimated_tokens": s.total_estimated_tokens,
            "agent_call_counts": s.agent_call_counts,
            "state_avg_duration_ms": {k: round(v, 1) for k, v in s.state_avg_duration_ms.items()},
            "uptime_seconds": round(time.monotonic() - self._start_time, 1),
        }
