"""Tests for the metrics collector."""

from src.observability.metrics import MetricsCollector, MetricsSummary


class TestMetricsCollector:
    def test_initial_state(self) -> None:
        mc = MetricsCollector()
        summary = mc.get_summary()
        assert summary.total_workflows == 0
        assert summary.completed_workflows == 0
        assert summary.failed_workflows == 0
        assert summary.avg_duration_ms == 0.0

    def test_record_workflow_start(self) -> None:
        mc = MetricsCollector()
        mc.record_workflow_start()
        mc.record_workflow_start()
        assert mc.get_summary().total_workflows == 2

    def test_record_workflow_end_completed(self) -> None:
        mc = MetricsCollector()
        mc.record_workflow_start()
        mc.record_workflow_end("completed", 1500.0)
        s = mc.get_summary()
        assert s.completed_workflows == 1
        assert s.failed_workflows == 0
        assert s.avg_duration_ms == 1500.0

    def test_record_workflow_end_failed(self) -> None:
        mc = MetricsCollector()
        mc.record_workflow_start()
        mc.record_workflow_end("failed", 500.0)
        s = mc.get_summary()
        assert s.completed_workflows == 0
        assert s.failed_workflows == 1

    def test_avg_duration(self) -> None:
        mc = MetricsCollector()
        mc.record_workflow_end("completed", 1000.0)
        mc.record_workflow_end("completed", 2000.0)
        assert mc.get_summary().avg_duration_ms == 1500.0

    def test_record_state_transition(self) -> None:
        mc = MetricsCollector()
        mc.record_state_transition("coding", "coder", 300.0, tokens=100)
        mc.record_state_transition("testing", "tester", 200.0, tokens=50)
        mc.record_state_transition("coding", "coder", 400.0, tokens=80)
        s = mc.get_summary()
        assert s.total_state_transitions == 3
        assert s.total_estimated_tokens == 230
        assert s.agent_call_counts["coder"] == 2
        assert s.agent_call_counts["tester"] == 1
        assert s.state_avg_duration_ms["coding"] == 350.0  # (300+400)/2

    def test_to_dict(self) -> None:
        mc = MetricsCollector()
        mc.record_workflow_start()
        mc.record_workflow_end("completed", 1000.0)
        d = mc.to_dict()
        assert isinstance(d, dict)
        assert d["total_workflows"] == 1
        assert d["completed_workflows"] == 1
        assert "uptime_seconds" in d
        assert d["uptime_seconds"] >= 0

    def test_prompt_completion_token_breakdown(self) -> None:
        mc = MetricsCollector()
        mc.record_state_transition(
            "coding",
            "coder",
            50.0,
            prompt_tokens=40,
            completion_tokens=10,
        )
        s = mc.get_summary()
        assert s.total_tokens == 50
        assert s.total_prompt_tokens == 40
        assert s.total_completion_tokens == 10
