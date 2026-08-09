"""Tests for metrics middleware."""
import pytest
from backend.metrics import MetricsCollector, record_latency, record_tokens, get_summary


def test_metrics_collector_initialization():
    mc = MetricsCollector()
    assert mc is not None
    assert hasattr(mc, "latencies")
    assert hasattr(mc, "tokens")


def test_record_latency():
    mc = MetricsCollector()
    record_latency(mc, 0.5, endpoint="/api/assist")
    record_latency(mc, 0.8, endpoint="/api/assist")
    summary = get_summary(mc)
    assert "p50" in summary
    assert "p95" in summary
    assert summary["count"] == 2


def test_record_tokens():
    mc = MetricsCollector()
    record_tokens(mc, prompt=100, completion=50)
    summary = get_summary(mc)
    assert summary["total_tokens"]["input"] == 100
    assert summary["total_tokens"]["output"] == 50


def test_p95_calculation():
    mc = MetricsCollector()
    for i in range(100):
        record_latency(mc, i / 100, endpoint="/test")
    summary = get_summary(mc)
    assert summary["p95"] >= 0.90
