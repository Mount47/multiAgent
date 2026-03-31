"""WebSocket connection manager for task event streams."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class TaskWebSocketManager:
    """Manage WebSocket subscribers per task id."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        # HITL: pending approval requests waiting for user response
        self._pending_approvals: dict[str, asyncio.Event] = {}
        self._approval_results: dict[str, dict[str, Any]] = {}

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

    # HITL: Request user approval for a workflow transition
    async def request_approval(
        self,
        task_id: str,
        checkpoint: str,
        content: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Pause workflow and wait for user approval.
        Returns the user's decision (approve/revise with feedback).
        """
        # Publish approval request event
        await self.publish(task_id, {
            "type": "approval_request",
            "checkpoint": checkpoint,
            "content": content,
        })

        # Create event to wait for response
        event = asyncio.Event()
        self._pending_approvals[task_id] = event

        try:
            # Wait for user response (with timeout)
            await asyncio.wait_for(event.wait(), timeout=300.0)  # 5 min timeout
            return self._approval_results.pop(task_id, {"action": "timeout"})
        except asyncio.TimeoutError:
            return {"action": "timeout", "reason": "User did not respond in time"}
        finally:
            self._pending_approvals.pop(task_id, None)

    # HITL: Handle approval response from user
    async def submit_approval_response(
        self,
        task_id: str,
        action: str,
        feedback: str = "",
    ) -> bool:
        """Submit user approval response to resume workflow."""
        event = self._pending_approvals.get(task_id)
        if not event:
            return False

        self._approval_results[task_id] = {
            "action": action,
            "feedback": feedback,
        }
        event.set()
        return True

