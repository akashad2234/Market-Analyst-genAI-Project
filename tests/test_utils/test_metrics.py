import time

import pytest

from utils.metrics import MetricsCollector, _LatencyRecord


class TestLatencyRecord:
    def test_initial_state(self):
        r = _LatencyRecord()
        assert r.count == 0
        assert r.avg_ms == 0.0

    def test_single_record(self):
        r = _LatencyRecord()
        r.record(150.0)
        assert r.count == 1
        assert r.avg_ms == 150.0
        assert r.min_ms == 150.0
        assert r.max_ms == 150.0

    def test_multiple_records(self):
        r = _LatencyRecord()
        r.record(100.0)
        r.record(200.0)
        r.record(300.0)
        assert r.count == 3
        assert r.avg_ms == pytest.approx(200.0)
        assert r.min_ms == 100.0
        assert r.max_ms == 300.0

    def test_to_dict(self):
        r = _LatencyRecord()
        r.record(50.0)
        d = r.to_dict()
        assert d["count"] == 1
        assert d["avg_ms"] == 50.0
        assert d["min_ms"] == 50.0
        assert d["max_ms"] == 50.0
        assert "total_ms" in d

    def test_to_dict_empty(self):
        r = _LatencyRecord()
        d = r.to_dict()
        assert d["count"] == 0
        assert d["avg_ms"] == 0.0
        assert d["min_ms"] == 0.0


class TestMetricsCollector:
    def test_increment(self):
        m = MetricsCollector()
        m.increment("test.counter")
        m.increment("test.counter")
        snap = m.snapshot()
        assert snap["counters"]["test.counter"] == 2

    def test_increment_custom_amount(self):
        m = MetricsCollector()
        m.increment("bulk", amount=5)
        snap = m.snapshot()
        assert snap["counters"]["bulk"] == 5

    def test_record_latency(self):
        m = MetricsCollector()
        m.record_latency("op", 42.5)
        snap = m.snapshot()
        assert snap["latencies"]["op"]["count"] == 1
        assert snap["latencies"]["op"]["avg_ms"] == 42.5

    def test_record_error(self):
        m = MetricsCollector()
        m.record_error("agent.fundamental")
        m.record_error("agent.fundamental")
        snap = m.snapshot()
        assert snap["errors"]["agent.fundamental"] == 2

    def test_track_context_manager_success(self):
        m = MetricsCollector()
        with m.track("fast_op"):
            time.sleep(0.01)
        snap = m.snapshot()
        assert snap["counters"]["fast_op"] == 1
        assert snap["latencies"]["fast_op"]["count"] == 1
        assert snap["latencies"]["fast_op"]["avg_ms"] > 0
        assert "fast_op" not in snap["errors"]

    def test_track_context_manager_error(self):
        m = MetricsCollector()
        with pytest.raises(ValueError):
            with m.track("fail_op"):
                raise ValueError("boom")
        snap = m.snapshot()
        assert snap["errors"]["fail_op"] == 1
        assert snap["latencies"]["fail_op"]["count"] == 1

    def test_snapshot_isolation(self):
        m = MetricsCollector()
        m.increment("a")
        snap1 = m.snapshot()
        m.increment("a")
        snap2 = m.snapshot()
        assert snap1["counters"]["a"] == 1
        assert snap2["counters"]["a"] == 2

    def test_reset(self):
        m = MetricsCollector()
        m.increment("x")
        m.record_latency("x", 10.0)
        m.record_error("x")
        m.reset()
        snap = m.snapshot()
        assert snap["counters"] == {}
        assert snap["latencies"] == {}
        assert snap["errors"] == {}
