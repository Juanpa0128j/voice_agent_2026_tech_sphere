"""Lightweight metrics collection for latency, token usage, and RAG queries."""
from typing import Dict, List


class MetricsCollector:
    def __init__(self) -> None:
        self.latencies: List[float] = []
        self.tokens: Dict[str, int] = {"input": 0, "output": 0}
        self.rag_queries: int = 0
        self.llm_calls: int = 0

    def record(self, name: str = "assist", latency_ms: float = 0.0, ok: bool = True, **kwargs) -> None:
        if latency_ms:
            self.latencies.append(latency_ms / 1000.0)
        if "prompt_tokens" in kwargs:
            self.tokens["input"] += kwargs["prompt_tokens"]
        if "completion_tokens" in kwargs:
            self.tokens["output"] += kwargs["completion_tokens"]

    def snapshot(self) -> Dict:
        latencies = sorted(self.latencies)
        p50 = latencies[len(latencies) // 2] if latencies else 0.0
        p95_idx = int(len(latencies) * 0.95)
        p95 = latencies[p95_idx] if latencies else 0.0
        cost_in = self.tokens["input"] / 1_000_000 * 0.59
        cost_out = self.tokens["output"] / 1_000_000 * 0.79
        return {
            "requests": len(latencies),
            "latency_ms": {
                "p50": p50 * 1000,
                "p95": p95 * 1000,
                "count": len(latencies),
            },
            "tokens": {
                "prompt": self.tokens["input"],
                "completion": self.tokens["output"],
                "total": self.tokens["input"] + self.tokens["output"],
            },
            "cost_usd": round(cost_in + cost_out, 6),
        }


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
