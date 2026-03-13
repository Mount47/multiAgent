"""Tests for persistence layer (database + repository)."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.persistence.models import Base, TaskEventModel, TaskModel
from src.persistence.repository import TaskRepository


@pytest_asyncio.fixture
async def session():
    """Create an in-memory SQLite database for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as sess:
        yield sess

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def repo(session: AsyncSession) -> TaskRepository:
    return TaskRepository(session)


class TestTaskRepository:
    @pytest.mark.asyncio
    async def test_create_task(self, repo: TaskRepository) -> None:
        task = await repo.create_task("id-1", "Build a calculator", "deepseek-chat")
        assert task.task_id == "id-1"
        assert task.task == "Build a calculator"
        assert task.provider == "deepseek-chat"
        assert task.status == "queued"

    @pytest.mark.asyncio
    async def test_get_task(self, repo: TaskRepository) -> None:
        await repo.create_task("id-2", "Build a todo app", "openai")
        result = await repo.get_task("id-2")
        assert result is not None
        assert result.task == "Build a todo app"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, repo: TaskRepository) -> None:
        result = await repo.get_task("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_tasks(self, repo: TaskRepository) -> None:
        await repo.create_task("id-a", "task A", "p1")
        await repo.create_task("id-b", "task B", "p2")
        tasks = await repo.list_tasks()
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_update_status(self, repo: TaskRepository) -> None:
        await repo.create_task("id-3", "task", "p")
        await repo.update_status("id-3", "running")
        task = await repo.get_task("id-3")
        assert task is not None
        assert task.status == "running"

    @pytest.mark.asyncio
    async def test_update_status_with_error(self, repo: TaskRepository) -> None:
        await repo.create_task("id-4", "task", "p")
        await repo.update_status("id-4", "failed", error="LLM timeout")
        task = await repo.get_task("id-4")
        assert task is not None
        assert task.status == "failed"
        assert task.error == "LLM timeout"

    @pytest.mark.asyncio
    async def test_add_event(self, repo: TaskRepository) -> None:
        await repo.create_task("id-5", "task", "p")
        event = await repo.add_event("id-5", "coder", "Here is the code...")
        assert event.task_id == "id-5"
        assert event.source == "coder"
        assert event.content == "Here is the code..."

    @pytest.mark.asyncio
    async def test_task_events_relationship(self, repo: TaskRepository) -> None:
        await repo.create_task("id-6", "task", "p")
        await repo.add_event("id-6", "pm", "Requirements analyzed")
        await repo.add_event("id-6", "coder", "Code written")
        task = await repo.get_task("id-6")
        assert task is not None
        assert len(task.events) == 2
        assert task.events[0].source == "pm"
        assert task.events[1].source == "coder"
