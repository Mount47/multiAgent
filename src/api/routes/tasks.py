"""Task CRUD and streaming routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from src.api.schemas.tasks import (
    CreateTaskRequest,
    CreateTaskResponse,
    TaskDetail,
    TaskEvent,
    TaskSummary,
)
from src.api.task_service import TaskService
from src.api.websocket.manager import TaskWebSocketManager

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def get_task_service() -> TaskService:
    from src.api.app import task_service

    return task_service


def get_ws_manager() -> TaskWebSocketManager:
    from src.api.app import ws_manager

    return ws_manager


@router.post("", response_model=CreateTaskResponse)
async def create_task(
    payload: CreateTaskRequest,
    service: TaskService = Depends(get_task_service),
) -> CreateTaskResponse:
    """Create a new workflow task."""
    record = await service.create_task(task=payload.task, provider=payload.provider)
    return CreateTaskResponse(task_id=record.task_id, status=record.status)


@router.get("", response_model=list[TaskSummary])
async def list_tasks(
    service: TaskService = Depends(get_task_service),
) -> list[TaskSummary]:
    """List tasks."""
    records = await service.list_tasks()
    return [
        TaskSummary(
            task_id=r.task_id,
            task=r.task,
            provider=r.provider,
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at,
            error=r.error,
        )
        for r in records
    ]


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskDetail:
    """Get task detail with event history."""
    record = await service.get_task(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskDetail(
        task_id=record.task_id,
        task=record.task,
        provider=record.provider,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        error=record.error,
        events=[
            TaskEvent(timestamp=e.timestamp, source=e.source, content=e.content)
            for e in record.events
        ],
    )


@router.websocket("/ws/{task_id}")
async def task_stream(
    websocket: WebSocket,
    task_id: str,
    service: TaskService = Depends(get_task_service),
    manager: TaskWebSocketManager = Depends(get_ws_manager),
) -> None:
    """Subscribe to real-time events for one task."""
    task = await service.get_task(task_id)
    if task is None:
        await websocket.close(code=1008, reason="Task not found")
        return

    await manager.connect(task_id, websocket)
    try:
        # Send existing backlog first for reconnect scenarios.
        for event in task.events:
            await websocket.send_json(
                {
                    "type": "event",
                    "timestamp": event.timestamp.isoformat(),
                    "source": event.source,
                    "content": event.content,
                }
            )
        await websocket.send_json({"type": "status", "status": task.status, "error": task.error})

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(task_id, websocket)

