"""Pydantic schemas for task APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["queued", "running", "completed", "failed"]


class CreateTaskRequest(BaseModel):
    """Task creation payload."""

    task: str = Field(min_length=1, max_length=4000)
    provider: str | None = Field(
        default=None,
        description="Optional provider override. Example: ollama-local/openai-gpt4/deepseek-chat",
    )


class CreateTaskResponse(BaseModel):
    """Task creation result."""

    task_id: str
    status: TaskStatus


class TaskEvent(BaseModel):
    """Streaming event item."""

    timestamp: datetime
    source: str
    content: str


class TaskSummary(BaseModel):
    """Task summary item used by list/detail APIs."""

    task_id: str
    task: str
    provider: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class TaskDetail(TaskSummary):
    """Task detail payload."""

    events: list[TaskEvent]

