"""Async CRUD repository for task persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.persistence.models import TaskEventModel, TaskModel


class TaskRepository:
    """Async repository wrapping SQLAlchemy operations for tasks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_task(
        self, task_id: str, task: str, provider: str, status: str = "queued"
    ) -> TaskModel:
        now = datetime.now(timezone.utc)
        obj = TaskModel(
            task_id=task_id,
            task=task,
            provider=provider,
            status=status,
            created_at=now,
            updated_at=now,
        )
        self._session.add(obj)
        await self._session.commit()
        return obj

    async def get_task(self, task_id: str) -> TaskModel | None:
        stmt = (
            select(TaskModel)
            .where(TaskModel.task_id == task_id)
            .options(selectinload(TaskModel.events))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tasks(self) -> list[TaskModel]:
        stmt = select(TaskModel).order_by(TaskModel.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self, task_id: str, status: str, error: str | None = None
    ) -> None:
        task = await self.get_task(task_id)
        if not task:
            return
        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        if error is not None:
            task.error = error
        await self._session.commit()

    async def add_event(
        self, task_id: str, source: str, content: str
    ) -> TaskEventModel:
        now = datetime.now(timezone.utc)
        event = TaskEventModel(
            task_id=task_id,
            timestamp=now,
            source=source,
            content=content,
        )
        self._session.add(event)
        await self._session.commit()
        return event
