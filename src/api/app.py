"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from src.api.routes.providers import router as providers_router
from src.api.routes.tasks import router as tasks_router
from src.api.routes.workflow import router as workflow_router
from src.api.task_service import TaskService
from src.api.websocket.manager import TaskWebSocketManager
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
task_service = TaskService(ws_manager=ws_manager, tracer=tracer, metrics=metrics)


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

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

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
            "transitions": [
                {
                    "from_state": t.from_state,
                    "to_state": t.to_state,
                    "agent": t.agent,
                    "duration_ms": round(t.duration_ms, 1),
                    "estimated_tokens": t.estimated_tokens,
                }
                for t in trace.transitions
            ],
        }

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
