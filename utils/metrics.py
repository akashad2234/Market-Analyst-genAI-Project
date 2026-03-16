"""In-memory metrics collection for observability.

Tracks analysis counts, per-agent latency, error counts, and request counts.
Thread-safe via threading.Lock.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator

from loguru import logger

_lock = threading.Lock()


@dataclass
class _LatencyRecord:
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count else 0.0

    def record(self, elapsed_ms: float) -> None:
        self.count += 1
        self.total_ms += elapsed_ms
        if elapsed_ms < self.min_ms:
            self.min_ms = elapsed_ms
        if elapsed_ms > self.max_ms:
            self.max_ms = elapsed_ms

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "avg_ms": round(self.avg_ms, 2),
            "min_ms": round(self.min_ms, 2) if self.count else 0.0,
            "max_ms": round(self.max_ms, 2),
            "total_ms": round(self.total_ms, 2),
        }


class MetricsCollector:
    """Singleton-style in-memory metrics store."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)
        self._latencies: dict[str, _LatencyRecord] = defaultdict(_LatencyRecord)
        self._errors: dict[str, int] = defaultdict(int)

    def increment(self, name: str, amount: int = 1) -> None:
        with _lock:
            self._counters[name] += amount

    def record_latency(self, name: str, elapsed_ms: float) -> None:
        with _lock:
            self._latencies[name].record(elapsed_ms)
        logger.debug("Latency [{}]: {:.1f}ms", name, elapsed_ms)

    def record_error(self, name: str) -> None:
        with _lock:
            self._errors[name] += 1

    @contextmanager
    def track(self, name: str) -> Generator[None, None, None]:
        """Context manager that records latency and increments counter."""
        start = time.perf_counter()
        try:
            yield
        except Exception:
            self.record_error(name)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.record_latency(name, elapsed_ms)
            self.increment(name)

    def snapshot(self) -> dict:
        """Return a point-in-time snapshot of all metrics."""
        with _lock:
            return {
                "counters": dict(self._counters),
                "latencies": {
                    k: v.to_dict() for k, v in self._latencies.items()
                },
                "errors": dict(self._errors),
            }

    def reset(self) -> None:
        """Clear all metrics (useful for testing)."""
        with _lock:
            self._counters.clear()
            self._latencies.clear()
            self._errors.clear()


metrics = MetricsCollector()
