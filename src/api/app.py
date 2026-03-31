"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from src.api.routes.providers import router as providers_router
from src.api.routes.tasks import router as tasks_router
from src.api.routes.workflow import router as workflow_router
from src.api.routes.workspace import router as workspace_router
from src.api.task_service import TaskService
from src.api.websocket.manager import TaskWebSocketManager
from src.memory.store import MemoryStore
from src.observability.metrics import MetricsCollector
from src.observability.tracer import WorkflowTracer
from src.persistence.database import init_db

project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")

logger = logging.getLogger(__name__)

# Shared instances
ws_manager = TaskWebSocketManager()
tracer = WorkflowTracer()
metrics = MetricsCollector()
try:
    memory_store: MemoryStore | None = MemoryStore()
except Exception as _mem_err:
    logger.warning("MemoryStore init failed, Memory disabled: %s", _mem_err)
    memory_store = None
task_service = TaskService(ws_manager=ws_manager, tracer=tracer, metrics=metrics, memory_store=memory_store)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database ready.")
    yield
    logger.info("Shutting down.")


def create_app() -> FastAPI:
    """Create configured FastAPI app."""
    app = FastAPI(
        title="Multi-Agent Dev API",
        version="0.1.0",
        description="Service API for multi-agent workflow execution",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(tasks_router)
    app.include_router(providers_router)
    app.include_router(workflow_router)
    app.include_router(workspace_router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/metrics")
    async def get_metrics() -> dict:
        return metrics.to_dict()

    @app.get("/api/traces/{task_id}")
    async def get_trace(task_id: str) -> dict:
        trace = tracer.get_trace(task_id)
        if not trace:
            return {"error": "Trace not found"}
        return {
            "task_id": trace.task_id,
            "started_at": trace.started_at.isoformat(),
            "ended_at": trace.ended_at.isoformat() if trace.ended_at else None,
            "duration_ms": round(trace.duration_ms, 1),
            "final_status": trace.final_status,
            "total_tokens": trace.total_tokens,
            "total_prompt_tokens": trace.total_prompt_tokens,
            "total_completion_tokens": trace.total_completion_tokens,
            "transitions": [
                {
                    "from_state": t.from_state,
                    "to_state": t.to_state,
                    "agent": t.agent,
                    "duration_ms": round(t.duration_ms, 1),
                    "estimated_tokens": t.estimated_tokens,
                    "prompt_tokens": t.prompt_tokens,
                    "completion_tokens": t.completion_tokens,
                }
                for t in trace.transitions
            ],
            "tool_calls": [
                {
                    "timestamp": tc.timestamp.isoformat(),
                    "tool_name": tc.tool_name,
                    "inputs": tc.inputs,
                    "output": tc.output,
                    "duration_ms": round(tc.duration_ms, 1),
                    "success": tc.success,
                    "error": tc.error,
                    "traceback": tc.traceback,
                }
                for tc in trace.tool_calls
            ],
        }

    @app.get("/api/memory/search")
    async def memory_search(q: str, n: int = 5) -> dict:
        """Search Memory collections. Returns matching conversations and code snippets."""
        if memory_store is None:
            return {"error": "Memory not available"}
        conv = memory_store.search_conversations(q, n_results=n)
        code = memory_store.search_code_snippets(q, n_results=n)
        return {"query": q, "conversations": conv, "code_snippets": code}

    @app.get("/api/memory/stats")
    async def memory_stats() -> dict:
        """Return record counts for each Memory collection."""
        if memory_store is None:
            return {"error": "Memory not available"}
        try:
            conv_count = memory_store._conversations.count()
            code_count = memory_store._code_snippets.count()
        except Exception as exc:
            return {"error": str(exc)}
        return {
            "conversations": conv_count,
            "code_snippets": code_count,
            "total": conv_count + code_count,
        }

    @app.delete("/api/memory/clear")
    async def memory_clear() -> dict:
        """Clear all Memory collections (useful for testing / resetting state)."""
        if memory_store is None:
            return {"error": "Memory not available"}
        memory_store.clear()
        return {"status": "cleared"}

    return app


app = create_app()


def run() -> None:
    """CLI entry for local API server."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
