"""WebSocket connection manager for task event streams."""

from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class TaskWebSocketManager:
    """Manage WebSocket subscribers per task id."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        """Accept and register a websocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections[task_id].add(websocket)

    async def disconnect(self, task_id: str, websocket: WebSocket) -> None:
        """Remove a websocket connection."""
        async with self._lock:
            conns = self._connections.get(task_id)
            if not conns:
                return
            conns.discard(websocket)
            if not conns:
                self._connections.pop(task_id, None)

    async def publish(self, task_id: str, message: dict) -> None:
        """Publish a JSON event to all subscribers of a task."""
        async with self._lock:
            conns = list(self._connections.get(task_id, set()))
        if not conns:
            return
        stale: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                existing = self._connections.get(task_id, set())
                for ws in stale:
                    existing.discard(ws)
                if not existing:
                    self._connections.pop(task_id, None)

