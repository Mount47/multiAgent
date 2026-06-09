"""Resilience layer for LLM model clients: classified retry + provider fallback.

AutoGen calls ``model_client.create(...)`` (and ``create_stream``) deep inside
the agent loop. When the underlying API raises a transient error (timeout,
429 rate limit, 5xx/503), the exception propagates all the way out of
``team.run_stream()`` and crashes the whole workflow — losing every prior step.

``ResilientChatCompletionClient`` wraps one or more real clients and owns the
retry policy explicitly:

  - transient errors  -> retry the same client with exponential backoff
                         (honouring a ``Retry-After`` header when present)
  - key/endpoint errors -> skip to the next (fallback) provider
  - malformed-request / unknown errors -> fail fast

Because it implements the same ``ChatCompletionClient`` interface and forwards
everything else to the primary client, agents are unaware they're wrapped.
"""

from __future__ import annotations

import asyncio
import logging
import random
from enum import Enum
from typing import Any, AsyncGenerator, Mapping, Sequence

import openai
from autogen_core import CancellationToken
from autogen_core.models import (
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    RequestUsage,
)
from autogen_core.tools import Tool, ToolSchema

logger = logging.getLogger(__name__)


class ErrorAction(Enum):
    """What to do when an LLM call raises."""

    RETRY = "retry"           # transient — back off and retry the same client
    NEXT_CLIENT = "next"      # client-specific — try the next fallback provider
    FATAL = "fatal"           # unrecoverable — raise immediately


def classify_error(exc: BaseException) -> ErrorAction:
    """Map an exception to a recovery action."""
    if isinstance(
        exc,
        (
            openai.APITimeoutError,
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.InternalServerError,
        ),
    ):
        return ErrorAction.RETRY
    if isinstance(exc, openai.BadRequestError):
        return ErrorAction.FATAL
    if isinstance(
        exc,
        (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError),
    ):
        return ErrorAction.NEXT_CLIENT
    if isinstance(exc, openai.APIStatusError):
        code = getattr(exc, "status_code", None)
        if code in (408, 409, 425, 429) or (code is not None and 500 <= code < 600):
            return ErrorAction.RETRY
        if code == 400:
            return ErrorAction.FATAL
        return ErrorAction.NEXT_CLIENT
    if isinstance(exc, openai.APIError):
        return ErrorAction.NEXT_CLIENT
    # Not an API error at all (bug, programming error) — don't mask it.
    return ErrorAction.FATAL


def _retry_after_seconds(exc: BaseException) -> float | None:
    """Extract a ``Retry-After`` hint (seconds) from a response, if present."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    raw = headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


class ResilientChatCompletionClient(ChatCompletionClient):
    """A ChatCompletionClient that adds retry + fallback around real clients.

    Args:
        clients: ``[(provider_name, client), ...]`` — first is primary, the
            rest are fallbacks tried in order. Must be non-empty.
        max_attempts: attempts per client for retryable errors (>= 1).
        base_delay: base seconds for exponential backoff.
        max_delay: cap on any single backoff sleep.
    """

    def __init__(
        self,
        clients: Sequence[tuple[str, ChatCompletionClient]],
        *,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        if not clients:
            raise ValueError("ResilientChatCompletionClient needs at least one client")
        self._clients = list(clients)
        self._primary = self._clients[0][1]
        self._max_attempts = max(1, max_attempts)
        self._base_delay = base_delay
        self._max_delay = max_delay

    # ------------------------------------------------------------------
    # Core: retry + fallback
    # ------------------------------------------------------------------

    def _backoff_delay(self, attempt: int, exc: BaseException) -> float:
        retry_after = _retry_after_seconds(exc)
        if retry_after is not None:
            return min(retry_after, self._max_delay)
        delay = min(self._base_delay * (2 ** (attempt - 1)), self._max_delay)
        return delay + random.uniform(0, self._base_delay)  # full jitter tail

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Any = "auto",
        json_output: Any = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: CancellationToken | None = None,
    ) -> CreateResult:
        last_exc: BaseException | None = None
        for idx, (name, client) in enumerate(self._clients):
            for attempt in range(1, self._max_attempts + 1):
                try:
                    return await client.create(
                        messages,
                        tools=tools,
                        tool_choice=tool_choice,
                        json_output=json_output,
                        extra_create_args=extra_create_args,
                        cancellation_token=cancellation_token,
                    )
                except Exception as exc:  # noqa: BLE001 — classified below
                    last_exc = exc
                    action = classify_error(exc)
                    if action is ErrorAction.FATAL:
                        raise
                    if action is ErrorAction.RETRY and attempt < self._max_attempts:
                        delay = self._backoff_delay(attempt, exc)
                        logger.warning(
                            "[LLM] %s failed (%s), retry %d/%d in %.1fs",
                            name, type(exc).__name__, attempt, self._max_attempts, delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    # Retries exhausted, or a next-client error: move on.
                    has_fallback = idx + 1 < len(self._clients)
                    logger.warning(
                        "[LLM] %s gave up (%s)%s",
                        name, type(exc).__name__,
                        f", falling back to {self._clients[idx + 1][0]}" if has_fallback else "",
                    )
                    break
        assert last_exc is not None
        raise last_exc

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Any = "auto",
        json_output: Any = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[str | CreateResult, None]:
        # Retry only protects the request before the first chunk is yielded;
        # once tokens are flowing we can't safely restart the stream.
        last_exc: BaseException | None = None
        for idx, (name, client) in enumerate(self._clients):
            for attempt in range(1, self._max_attempts + 1):
                started = False
                try:
                    async for item in client.create_stream(
                        messages,
                        tools=tools,
                        tool_choice=tool_choice,
                        json_output=json_output,
                        extra_create_args=extra_create_args,
                        cancellation_token=cancellation_token,
                    ):
                        started = True
                        yield item
                    return
                except Exception as exc:  # noqa: BLE001
                    if started:
                        raise  # mid-stream failure — not safe to retry
                    last_exc = exc
                    action = classify_error(exc)
                    if action is ErrorAction.FATAL:
                        raise
                    if action is ErrorAction.RETRY and attempt < self._max_attempts:
                        delay = self._backoff_delay(attempt, exc)
                        logger.warning(
                            "[LLM] %s stream failed (%s), retry %d/%d in %.1fs",
                            name, type(exc).__name__, attempt, self._max_attempts, delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    break
        assert last_exc is not None
        raise last_exc

    # ------------------------------------------------------------------
    # Delegation to the primary client for everything else
    # ------------------------------------------------------------------

    @property
    def model_info(self):  # type: ignore[override]
        return self._primary.model_info

    @property
    def capabilities(self):  # type: ignore[override]
        return self._primary.capabilities

    def actual_usage(self) -> RequestUsage:
        return self._primary.actual_usage()

    def total_usage(self) -> RequestUsage:
        return self._primary.total_usage()

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return self._primary.count_tokens(messages, tools=tools)

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []) -> int:
        return self._primary.remaining_tokens(messages, tools=tools)

    async def close(self) -> None:
        for _, client in self._clients:
            try:
                await client.close()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass

    def __getattr__(self, item: str) -> Any:
        # Safety net for any non-overridden member (component_*, dump_component...).
        return getattr(self.__dict__["_primary"], item)
