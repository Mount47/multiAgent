"""Unit tests for the LLM resilience layer (retry + fallback)."""

from __future__ import annotations

import httpx
import openai
import pytest
from autogen_core.models import CreateResult, RequestUsage

from src.models.resilient_client import (
    ErrorAction,
    ResilientChatCompletionClient,
    classify_error,
)


# --- helpers to construct real openai exceptions -------------------------

def _request() -> httpx.Request:
    return httpx.Request("POST", "https://example.test/v1/chat/completions")


def _response(status: int, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(status, request=_request(), headers=headers or {})


def rate_limit(headers: dict | None = None) -> openai.RateLimitError:
    return openai.RateLimitError("429", response=_response(429, headers), body=None)


def server_error() -> openai.InternalServerError:
    return openai.InternalServerError("503", response=_response(503), body=None)


def auth_error() -> openai.AuthenticationError:
    return openai.AuthenticationError("401", response=_response(401), body=None)


def bad_request() -> openai.BadRequestError:
    return openai.BadRequestError("400", response=_response(400), body=None)


def ok_result(content: str = "ok") -> CreateResult:
    return CreateResult(
        finish_reason="stop",
        content=content,
        usage=RequestUsage(prompt_tokens=1, completion_tokens=1),
        cached=False,
    )


class FakeClient:
    """Minimal ChatCompletionClient stand-in driven by a scripted behavior list.

    Each entry is either an Exception (raised) or a CreateResult (returned).
    """

    def __init__(self, behaviors: list):
        self._behaviors = list(behaviors)
        self.calls = 0
        self.model_info = {"family": "fake"}

    async def create(self, *args, **kwargs):
        self.calls += 1
        item = self._behaviors.pop(0) if self._behaviors else ok_result()
        if isinstance(item, BaseException):
            raise item
        return item

    async def close(self):  # pragma: no cover - trivial
        pass


def _resilient(*clients, max_attempts=3):
    pairs = [(f"p{i}", c) for i, c in enumerate(clients)]
    return ResilientChatCompletionClient(
        pairs, max_attempts=max_attempts, base_delay=0.0, max_delay=0.0
    )


# --- classification ------------------------------------------------------

@pytest.mark.parametrize(
    "exc, expected",
    [
        (rate_limit(), ErrorAction.RETRY),
        (server_error(), ErrorAction.RETRY),
        (openai.APITimeoutError(request=_request()), ErrorAction.RETRY),
        (auth_error(), ErrorAction.NEXT_CLIENT),
        (bad_request(), ErrorAction.FATAL),
        (ValueError("bug"), ErrorAction.FATAL),
    ],
)
def test_classify_error(exc, expected):
    assert classify_error(exc) is expected


# --- retry behavior ------------------------------------------------------

@pytest.mark.asyncio
async def test_retries_transient_then_succeeds():
    client = FakeClient([server_error(), rate_limit(), ok_result("done")])
    resilient = _resilient(client)
    result = await resilient.create([])
    assert result.content == "done"
    assert client.calls == 3


@pytest.mark.asyncio
async def test_gives_up_after_max_attempts():
    client = FakeClient([server_error(), server_error(), server_error()])
    resilient = _resilient(client, max_attempts=3)
    with pytest.raises(openai.InternalServerError):
        await resilient.create([])
    assert client.calls == 3  # no fallback configured


@pytest.mark.asyncio
async def test_fatal_error_not_retried():
    client = FakeClient([bad_request(), ok_result()])
    resilient = _resilient(client)
    with pytest.raises(openai.BadRequestError):
        await resilient.create([])
    assert client.calls == 1  # failed fast, never retried


# --- fallback behavior ---------------------------------------------------

@pytest.mark.asyncio
async def test_falls_back_when_primary_exhausted():
    primary = FakeClient([server_error(), server_error(), server_error()])
    backup = FakeClient([ok_result("from-backup")])
    resilient = _resilient(primary, backup, max_attempts=3)
    result = await resilient.create([])
    assert result.content == "from-backup"
    assert primary.calls == 3
    assert backup.calls == 1


@pytest.mark.asyncio
async def test_next_client_error_skips_to_fallback_immediately():
    primary = FakeClient([auth_error()])  # key problem — don't retry, switch
    backup = FakeClient([ok_result("from-backup")])
    resilient = _resilient(primary, backup, max_attempts=3)
    result = await resilient.create([])
    assert result.content == "from-backup"
    assert primary.calls == 1  # not retried, jumped straight to fallback


@pytest.mark.asyncio
async def test_raises_last_error_when_all_clients_exhausted():
    primary = FakeClient([server_error(), server_error(), server_error()])
    backup = FakeClient([rate_limit(), rate_limit(), rate_limit()])
    resilient = _resilient(primary, backup, max_attempts=3)
    with pytest.raises(openai.RateLimitError):  # last client's last error
        await resilient.create([])
    assert primary.calls == 3
    assert backup.calls == 3
