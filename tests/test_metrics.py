"""Tests for metrics middleware."""
import pytest
from backend.metrics import MetricsCollector


def test_metrics_collector_initialization():
    mc = MetricsCollector()
    assert mc is not None
    assert hasattr(mc, "latencies")
    assert hasattr(mc, "tokens")
