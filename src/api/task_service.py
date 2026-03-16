"""Task orchestration service with persistence and observability."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from src.api.websocket.manager import TaskWebSocketManager
from src.models.factory import ModelClientFactory
from src.observability.metrics import MetricsCollector
from src.observability.tool_observer import ToolObservation, tool_observer_context
from src.observability.tracer import WorkflowTracer
from src.orchestration.team_builder import build_team
from src.persistence.database import get_db
from src.persistence.repository import TaskRepository

logger = logging.getLogger(__name__)

# Reverse lookup: agent name → workflow state name
_AGENT_STATE_MAP: dict[str, str] = {
    "product_manager": "requirements_analysis",
    "architect": "architecture_design",
    "coder": "coding",
    "tester": "testing",
    "reviewer": "code_review",
}

TaskStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class TaskEventRecord:
    timestamp: datetime
    source: str
    content: str


@dataclass
class TaskRecord:
    task_id: str
    task: str
    provider: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    events: list[TaskEventRecord] = field(default_factory=list)


class TaskService:
    """Task lifecycle + workflow execution with DB persistence and tracing."""

    def __init__(
        self,
        ws_manager: TaskWebSocketManager,
        tracer: WorkflowTracer | None = None,
        metrics: MetricsCollector | None = None,
    ) -> None:
        self._ws_manager = ws_manager
        self._tracer = tracer or WorkflowTracer()
        self._metrics = metrics or MetricsCollector()
        # In-memory cache for fast reads; DB is source of truth
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()

    @property
    def tracer(self) -> WorkflowTracer:
        return self._tracer

    @property
    def metrics(self) -> MetricsCollector:
        return self._metrics

    async def create_task(self, task: str, provider: str | None = None) -> TaskRecord:
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        provider_name = provider or os.getenv("DEFAULT_MODEL", "deepseek-chat")
        record = TaskRecord(
            task_id=task_id,
            task=task,
            provider=provider_name,
            status="queued",
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._tasks[task_id] = record

        # Persist to DB
        try:
            session = await get_db()
            repo = TaskRepository(session)
            await repo.create_task(task_id, task, provider_name)
            await session.close()
        except Exception:
            logger.warning("DB persist failed for task %s, continuing in-memory", task_id[:8])

        asyncio.create_task(self._run_task(task_id, provider))
        return record

    async def list_tasks(self) -> list[TaskRecord]:
        async with self._lock:
            items = list(self._tasks.values())
        return sorted(items, key=lambda x: x.created_at, reverse=True)

    async def get_task(self, task_id: str) -> TaskRecord | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def _run_task(self, task_id: str, provider: str | None) -> None:
        await self._set_status(task_id, "running")
        self._tracer.start_workflow(task_id)
        self._metrics.record_workflow_start()

        try:
            model_factory = ModelClientFactory()
            if provider:
                self._apply_provider_override(model_factory, provider)

            team = await build_team(model_factory=model_factory)
            task = await self.get_task(task_id)
            if task is None:
                return

            loop = asyncio.get_running_loop()

            def _tool_callback(observation: ToolObservation) -> None:
                try:
                    loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self._record_tool_observation(task_id, observation))
                    )
                except RuntimeError:
                    logger.debug("Event loop closed while recording tool observation")

            current_agent = ""
            state_prompt_tokens = 0
            state_completion_tokens = 0

            with tool_observer_context(_tool_callback):
                async for event in team.run_stream(task=task.task):
                    if not hasattr(event, "source") or not hasattr(event, "content"):
                        continue

                    agent_name = str(event.source)
                    content = self._normalize_content(event.content)
                    prompt_tokens, completion_tokens = self._extract_usage_tokens(event)
                    is_workflow_agent = agent_name in _AGENT_STATE_MAP

                    # Track state transitions for workflow agents only.
                    if is_workflow_agent and agent_name != current_agent:
                        prev_agent = current_agent
                        if prev_agent:
                            self._tracer.exit_state(
                                task_id,
                                prompt_tokens=state_prompt_tokens,
                                completion_tokens=state_completion_tokens,
                            )
                        self._tracer.enter_state(task_id, state=agent_name, agent=agent_name)
                        current_agent = agent_name
                        state_prompt_tokens = 0
                        state_completion_tokens = 0

                        if agent_name == "coder" and prev_agent in ("tester", "reviewer"):
                            state_name = "revision"
                        else:
                            state_name = _AGENT_STATE_MAP.get(agent_name, agent_name)

                        await self._ws_manager.publish(
                            task_id,
                            {
                                "type": "state_change",
                                "agent": agent_name,
                                "state": state_name,
                            },
                        )

                    if is_workflow_agent:
                        state_prompt_tokens += prompt_tokens
                        state_completion_tokens += completion_tokens

                    await self._publish_event(
                        task_id,
                        TaskEventRecord(
                            timestamp=datetime.now(timezone.utc),
                            source=agent_name,
                            content=content,
                        ),
                    )

            # Workflow completed
            if current_agent:
                self._tracer.exit_state(
                    task_id,
                    prompt_tokens=state_prompt_tokens,
                    completion_tokens=state_completion_tokens,
                )
            trace = self._tracer.end_workflow(task_id, status="completed")
            if trace:
                self._metrics.record_workflow_end("completed", trace.duration_ms)
                for t in trace.transitions:
                    self._metrics.record_state_transition(
                        t.from_state,
                        t.agent,
                        t.duration_ms,
                        tokens=t.estimated_tokens,
                        prompt_tokens=t.prompt_tokens,
                        completion_tokens=t.completion_tokens,
                    )

            await self._set_status(task_id, "completed")
            await self._ws_manager.publish(task_id, {"type": "status", "status": "completed"})

        except Exception as exc:
            tb = traceback.format_exc()
            await self._publish_event(
                task_id,
                TaskEventRecord(
                    timestamp=datetime.now(timezone.utc),
                    source="system_error",
                    content=f"{exc}\n\n{tb}",
                ),
            )
            trace = self._tracer.end_workflow(task_id, status="failed")
            if trace:
                self._metrics.record_workflow_end("failed", trace.duration_ms)
            await self._set_failed(task_id, str(exc))
            await self._ws_manager.publish(
                task_id,
                {"type": "status", "status": "failed", "error": str(exc)},
            )

    @staticmethod
    def _apply_provider_override(model_factory: ModelClientFactory, provider: str) -> None:
        if provider not in model_factory.config.providers:
            available = ", ".join(model_factory.config.providers.keys())
            raise ValueError(f"Unknown provider '{provider}'. Available: {available}")
        for role in model_factory.config.agent_models.keys():
            model_factory.config.agent_models[role] = provider

    async def _set_status(self, task_id: str, status: TaskStatus) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task.status = status
            task.updated_at = datetime.now(timezone.utc)
        # Persist
        try:
            session = await get_db()
            repo = TaskRepository(session)
            await repo.update_status(task_id, status)
            await session.close()
        except Exception:
            logger.warning("DB status update failed for %s", task_id[:8])

    async def _set_failed(self, task_id: str, error: str) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task.status = "failed"
            task.error = error
            task.updated_at = datetime.now(timezone.utc)
        try:
            session = await get_db()
            repo = TaskRepository(session)
            await repo.update_status(task_id, "failed", error=error)
            await session.close()
        except Exception:
            logger.warning("DB fail update failed for %s", task_id[:8])

    async def _publish_event(self, task_id: str, payload: TaskEventRecord) -> None:
        await self._append_event(task_id, payload)
        await self._ws_manager.publish(
            task_id,
            {
                "type": "event",
                "timestamp": payload.timestamp.isoformat(),
                "source": payload.source,
                "content": payload.content,
            },
        )

    async def _record_tool_observation(self, task_id: str, observation: ToolObservation) -> None:
        self._tracer.record_tool_call(
            task_id=task_id,
            tool_name=observation.tool_name,
            inputs=observation.inputs,
            output=observation.output,
            duration_ms=observation.duration_ms,
            success=observation.success,
            error=observation.error,
            traceback=observation.traceback,
            timestamp=observation.timestamp,
        )
        await self._publish_event(
            task_id,
            TaskEventRecord(
                timestamp=observation.timestamp,
                source=f"tool:{observation.tool_name}",
                content=self._format_tool_observation(observation),
            ),
        )

    @staticmethod
    def _format_tool_observation(observation: ToolObservation) -> str:
        status = "SUCCESS" if observation.success else "FAILED"
        parts = [
            f"[TOOL] {observation.tool_name} {status} ({observation.duration_ms:.1f}ms)",
            f"input={observation.inputs}",
            f"output={observation.output}",
        ]
        if observation.error:
            parts.append(f"error={observation.error}")
        if observation.traceback:
            parts.append(f"traceback=\n{observation.traceback}")
        return "\n".join(parts)

    @staticmethod
    def _extract_usage_tokens(event: Any) -> tuple[int, int]:
        usage = getattr(event, "models_usage", None)
        if usage is None:
            return 0, 0
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        return prompt_tokens, completion_tokens

    @staticmethod
    def _normalize_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False, default=str)
        except Exception:
            return str(content)

    async def _append_event(self, task_id: str, event: TaskEventRecord) -> None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task.events.append(event)
            task.updated_at = event.timestamp
        try:
            session = await get_db()
            repo = TaskRepository(session)
            await repo.add_event(task_id, event.source, event.content)
            await session.close()
        except Exception:
            pass  # Non-critical, in-memory still has it
