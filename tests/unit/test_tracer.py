"""Tests for the observability tracer."""

import time

from src.observability.tracer import WorkflowTracer


class TestWorkflowTracer:
    def test_start_and_end_workflow(self) -> None:
        tracer = WorkflowTracer()
        tracer.start_workflow("task-1")
        trace = tracer.end_workflow("task-1", status="completed")
        assert trace is not None
        assert trace.task_id == "task-1"
        assert trace.final_status == "completed"
        assert trace.ended_at is not None
        assert trace.duration_ms >= 0

    def test_enter_and_exit_state(self) -> None:
        tracer = WorkflowTracer()
        tracer.start_workflow("task-2")
        tracer.enter_state("task-2", state="coding", agent="coder")
        tracer.exit_state("task-2", estimated_tokens=100)
        trace = tracer.end_workflow("task-2")
        assert trace is not None
        assert len(trace.transitions) == 1
        assert trace.transitions[0].from_state == "coding"
        assert trace.transitions[0].agent == "coder"
        assert trace.transitions[0].estimated_tokens == 100

    def test_multiple_state_transitions(self) -> None:
        tracer = WorkflowTracer()
        tracer.start_workflow("task-3")
        tracer.enter_state("task-3", state="requirements", agent="pm")
        tracer.enter_state("task-3", state="coding", agent="coder")
        tracer.enter_state("task-3", state="testing", agent="tester")
        tracer.exit_state("task-3")
        trace = tracer.end_workflow("task-3")
        assert trace is not None
        assert len(trace.transitions) == 3

    def test_total_tokens_aggregated(self) -> None:
        tracer = WorkflowTracer()
        tracer.start_workflow("task-4")
        tracer.enter_state("task-4", state="s1", agent="a1")
        tracer.exit_state("task-4", estimated_tokens=50)
        tracer.enter_state("task-4", state="s2", agent="a2")
        tracer.exit_state("task-4", estimated_tokens=30)
        trace = tracer.end_workflow("task-4")
        assert trace is not None
        assert trace.total_tokens == 80

    def test_get_trace(self) -> None:
        tracer = WorkflowTracer()
        assert tracer.get_trace("nonexistent") is None
        tracer.start_workflow("task-5")
        assert tracer.get_trace("task-5") is not None

    def test_list_traces(self) -> None:
        tracer = WorkflowTracer()
        tracer.start_workflow("a")
        tracer.start_workflow("b")
        assert len(tracer.list_traces()) == 2

    def test_end_nonexistent_workflow(self) -> None:
        tracer = WorkflowTracer()
        trace = tracer.end_workflow("nonexistent")
        assert trace is None

    def test_prompt_completion_token_aggregation(self) -> None:
        tracer = WorkflowTracer()
        tracer.start_workflow("task-6")
        tracer.enter_state("task-6", state="coding", agent="coder")
        tracer.exit_state("task-6", prompt_tokens=120, completion_tokens=30)
        trace = tracer.end_workflow("task-6")
        assert trace is not None
        assert trace.total_prompt_tokens == 120
        assert trace.total_completion_tokens == 30
        assert trace.total_tokens == 150
        assert trace.transitions[0].estimated_tokens == 150

    def test_tool_call_recording(self) -> None:
        tracer = WorkflowTracer()
        tracer.start_workflow("task-7")
        tracer.record_tool_call(
            task_id="task-7",
            tool_name="read_file",
            inputs='{"filename":"a.py"}',
            output="print('ok')",
            duration_ms=12.5,
            success=True,
        )
        trace = tracer.end_workflow("task-7")
        assert trace is not None
        assert len(trace.tool_calls) == 1
        call = trace.tool_calls[0]
        assert call.tool_name == "read_file"
        assert call.success is True
        assert call.duration_ms == 12.5
