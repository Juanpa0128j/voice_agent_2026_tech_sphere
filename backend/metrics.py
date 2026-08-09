"""Lightweight metrics collection for latency, token usage, and RAG queries."""
from typing import Dict, List


class MetricsCollector:
    def __init__(self) -> None:
        self.latencies: List[float] = []
        self.tokens: Dict[str, int] = {"input": 0, "output": 0}
        self.rag_queries: int = 0
        self.llm_calls: int = 0


_global_collector = MetricsCollector()


def record_latency(
    collector: MetricsCollector, latency_seconds: float, endpoint: str = ""
) -> None:
    collector.latencies.append(latency_seconds)


def record_tokens(
    collector: MetricsCollector, prompt: int = 0, completion: int = 0
) -> None:
    collector.tokens["input"] += prompt
    collector.tokens["output"] += completion


def get_summary(collector: MetricsCollector) -> Dict:
    latencies = sorted(collector.latencies)
    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p95_idx = int(len(latencies) * 0.95)
    p95 = latencies[p95_idx] if latencies else 0.0

    cost_input = collector.tokens["input"] / 1_000_000 * 0.59
    cost_output = collector.tokens["output"] / 1_000_000 * 0.79

    return {
        "count": len(latencies),
        "p50": p50,
        "p95": p95,
        "total_tokens": collector.tokens.copy(),
        "estimated_cost_usd": cost_input + cost_output,
    }
