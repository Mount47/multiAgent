"""Tool-call observability helpers: decorator + scoped callback context."""

from __future__ import annotations

import inspect
import json
import logging
import time
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

_MAX_INPUT_CHARS = 2000
_MAX_OUTPUT_CHARS = 4000
_SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "apikey", "authorization"}
_OBSERVER: ContextVar[Callable[["ToolObservation"], None] | None] = ContextVar(
    "tool_observer_callback", default=None
)


@dataclass
class ToolObservation:
    """Single tool call observation payload."""

    tool_name: str
    inputs: str
    output: str
    duration_ms: float
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    traceback: str | None = None


@contextmanager
def tool_observer_context(callback: Callable[[ToolObservation], None]):
    """Bind an observer callback in current execution context."""

    token = _OBSERVER.set(callback)
    try:
        yield
    finally:
        _OBSERVER.reset(token)


def observe_tool_call(name: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for tool functions to record input/output/duration/success."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        tool_name = name or func.__name__

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs):  # type: ignore[misc]
                started = time.perf_counter()
                inputs = _serialize_inputs(func, args, kwargs)
                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:
                    tb = traceback.format_exc()
                    _emit(
                        ToolObservation(
                            tool_name=tool_name,
                            inputs=inputs,
                            output=_truncate(str(exc), _MAX_OUTPUT_CHARS),
                            duration_ms=(time.perf_counter() - started) * 1000,
                            success=False,
                            error=str(exc),
                            traceback=tb,
                        )
                    )
                    raise

                output = _serialize_output(result)
                _emit(
                    ToolObservation(
                        tool_name=tool_name,
                        inputs=inputs,
                        output=output,
                        duration_ms=(time.perf_counter() - started) * 1000,
                        success=_is_success(result),
                    )
                )
                return result

            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs):  # type: ignore[misc]
            started = time.perf_counter()
            inputs = _serialize_inputs(func, args, kwargs)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                tb = traceback.format_exc()
                _emit(
                    ToolObservation(
                        tool_name=tool_name,
                        inputs=inputs,
                        output=_truncate(str(exc), _MAX_OUTPUT_CHARS),
                        duration_ms=(time.perf_counter() - started) * 1000,
                        success=False,
                        error=str(exc),
                        traceback=tb,
                    )
                )
                raise

            output = _serialize_output(result)
            _emit(
                ToolObservation(
                    tool_name=tool_name,
                    inputs=inputs,
                    output=output,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    success=_is_success(result),
                )
            )
            return result

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _emit(record: ToolObservation) -> None:
    callback = _OBSERVER.get()
    if callback is None:
        logger.info(
            "[tool] %s success=%s duration=%.1fms", record.tool_name, record.success, record.duration_ms
        )
        return
    try:
        callback(record)
    except Exception:
        logger.exception("tool observer callback failed")


def _serialize_inputs(func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    try:
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        payload = {k: _sanitize(k, v) for k, v in bound.arguments.items()}
        return _truncate(json.dumps(payload, ensure_ascii=False, default=str), _MAX_INPUT_CHARS)
    except Exception:
        raw = {"args": [str(x) for x in args], "kwargs": {k: str(v) for k, v in kwargs.items()}}
        return _truncate(json.dumps(raw, ensure_ascii=False), _MAX_INPUT_CHARS)


def _serialize_output(result: Any) -> str:
    if isinstance(result, str):
        return _truncate(result, _MAX_OUTPUT_CHARS)
    try:
        return _truncate(json.dumps(result, ensure_ascii=False, default=str), _MAX_OUTPUT_CHARS)
    except Exception:
        return _truncate(str(result), _MAX_OUTPUT_CHARS)


def _sanitize(key: str, value: Any) -> Any:
    lowered = key.lower()
    if lowered in _SENSITIVE_KEYS or any(s in lowered for s in _SENSITIVE_KEYS):
        return "***"
    if isinstance(value, dict):
        return {k: _sanitize(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(key, v) for v in value]
    if isinstance(value, tuple):
        return tuple(_sanitize(key, v) for v in value)
    if isinstance(value, str):
        return _truncate(value, 800)
    return value


def _is_success(result: Any) -> bool:
    if isinstance(result, str):
        return not result.strip().lower().startswith("[error]")
    return True


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}... [truncated]"
