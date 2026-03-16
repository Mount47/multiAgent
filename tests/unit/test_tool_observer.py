"""Tests for tool call observability decorator/context."""

from __future__ import annotations

import pytest

from src.observability.tool_observer import ToolObservation, observe_tool_call, tool_observer_context


class TestToolObserver:
    @pytest.mark.asyncio
    async def test_async_tool_success_observed(self) -> None:
        records: list[ToolObservation] = []

        @observe_tool_call("demo_tool")
        async def demo_tool(text: str) -> str:
            return text.upper()

        with tool_observer_context(records.append):
            result = await demo_tool("hello")

        assert result == "HELLO"
        assert len(records) == 1
        assert records[0].tool_name == "demo_tool"
        assert records[0].success is True
        assert "hello" in records[0].inputs
        assert "HELLO" in records[0].output
        assert records[0].duration_ms >= 0

    def test_sync_tool_exception_observed(self) -> None:
        records: list[ToolObservation] = []

        @observe_tool_call("failing_tool")
        def failing_tool(x: int) -> str:
            raise ValueError(f"bad value: {x}")

        with pytest.raises(ValueError):
            with tool_observer_context(records.append):
                failing_tool(42)

        assert len(records) == 1
        assert records[0].tool_name == "failing_tool"
        assert records[0].success is False
        assert "bad value: 42" in records[0].output
        assert records[0].traceback is not None

    def test_error_string_marked_failed(self) -> None:
        records: list[ToolObservation] = []

        @observe_tool_call("error_string_tool")
        def error_string_tool() -> str:
            return "[ERROR] something failed"

        with tool_observer_context(records.append):
            _ = error_string_tool()

        assert len(records) == 1
        assert records[0].success is False
