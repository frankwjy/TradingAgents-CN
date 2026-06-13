"""
Tests for FallbackTracker - data source fallback transparency
"""
import pytest
import time
from unittest.mock import MagicMock, patch
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.data_sources.fallback_tracker import (
    FallbackTracker, FallbackAttempt, FallbackEvent, get_fallback_tracker
)


class TestFallbackAttempt:
    """Test FallbackAttempt dataclass"""

    def test_create_attempt(self):
        attempt = FallbackAttempt(
            source_name="tushare",
            success=True,
            duration_ms=150.5,
        )
        assert attempt.source_name == "tushare"
        assert attempt.success is True
        assert attempt.duration_ms == 150.5
        assert attempt.error is None
        assert attempt.error_type is None

    def test_create_failed_attempt(self):
        attempt = FallbackAttempt(
            source_name="akshare",
            success=False,
            duration_ms=50.0,
            error="Connection timeout",
            error_type="TimeoutError",
        )
        assert attempt.success is False
        assert attempt.error == "Connection timeout"
        assert attempt.error_type == "TimeoutError"

    def test_attempt_to_dict(self):
        attempt = FallbackAttempt(
            source_name="tushare",
            success=True,
            duration_ms=150.5,
        )
        d = attempt.to_dict()
        assert d["source_name"] == "tushare"
        assert d["success"] is True
        assert d["duration_ms"] == 150.5
        assert d["error"] is None


class TestFallbackEvent:
    """Test FallbackEvent dataclass"""

    def test_create_event(self):
        event = FallbackEvent(
            data_type="stock_list",
            primary_source="tushare",
            final_source="akshare",
            success=True,
            total_duration_ms=500.0,
            attempts=[
                FallbackAttempt("tushare", False, 200.0, "API error", "Exception"),
                FallbackAttempt("akshare", True, 300.0),
            ],
        )
        assert event.data_type == "stock_list"
        assert event.primary_source == "tushare"
        assert event.final_source == "akshare"
        assert event.success is True
        assert len(event.attempts) == 2
        assert event.fallback_count == 1  # primary failed, one fallback

    def test_event_no_fallback(self):
        event = FallbackEvent(
            data_type="stock_list",
            primary_source="tushare",
            final_source="tushare",
            success=True,
            total_duration_ms=100.0,
            attempts=[
                FallbackAttempt("tushare", True, 100.0),
            ],
        )
        assert event.fallback_count == 0

    def test_event_all_failed(self):
        event = FallbackEvent(
            data_type="kline",
            primary_source="tushare",
            final_source=None,
            success=False,
            total_duration_ms=800.0,
            attempts=[
                FallbackAttempt("tushare", False, 200.0, "err1", "E1"),
                FallbackAttempt("akshare", False, 300.0, "err2", "E2"),
                FallbackAttempt("baostock", False, 300.0, "err3", "E3"),
            ],
        )
        assert event.fallback_count == 2
        assert event.success is False

    def test_event_to_dict(self):
        event = FallbackEvent(
            data_type="news",
            primary_source="mongodb",
            final_source="tushare",
            success=True,
            total_duration_ms=400.0,
            attempts=[
                FallbackAttempt("mongodb", False, 100.0, "no data", "ValueError"),
                FallbackAttempt("tushare", True, 300.0),
            ],
        )
        d = event.to_dict()
        assert d["data_type"] == "news"
        assert d["fallback_count"] == 1
        assert len(d["attempts"]) == 2

    def test_event_fallback_chain(self):
        event = FallbackEvent(
            data_type="stock_list",
            primary_source="tushare",
            final_source="baostock",
            success=True,
            total_duration_ms=900.0,
            attempts=[
                FallbackAttempt("tushare", False, 200.0, "err", "E"),
                FallbackAttempt("akshare", False, 300.0, "err", "E"),
                FallbackAttempt("baostock", True, 400.0),
            ],
        )
        assert event.fallback_chain == ["tushare", "akshare", "baostock"]


class TestFallbackTracker:
    """Test FallbackTracker class"""

    def test_tracker_starts_empty(self):
        tracker = FallbackTracker()
        assert len(tracker.events) == 0
        assert len(tracker.recent_events()) == 0

    def test_begin_and_finish(self):
        tracker = FallbackTracker()
        tracker.begin("stock_list", "tushare")
        assert tracker._current_event is not None
        assert tracker._current_event.data_type == "stock_list"
        assert tracker._current_event.primary_source == "tushare"

        event = tracker.finish("akshare", success=True)
        assert event.final_source == "akshare"
        assert event.success is True
        assert len(tracker.events) == 1

    def test_record_attempt(self):
        tracker = FallbackTracker()
        tracker.begin("stock_list", "tushare")

        tracker.record_attempt("tushare", success=False, duration_ms=200.0,
                               error="API timeout", error_type="TimeoutError")
        tracker.record_attempt("akshare", success=True, duration_ms=300.0)

        event = tracker.finish("akshare", success=True)
        assert len(event.attempts) == 2
        assert event.attempts[0].success is False
        assert event.attempts[1].success is True

    def test_recent_events_limit(self):
        tracker = FallbackTracker()
        for i in range(15):
            tracker.begin(f"type_{i}", "tushare")
            tracker.finish("akshare", success=True)

        assert len(tracker.events) == 15
        recent = tracker.recent_events(limit=5)
        assert len(recent) == 5
        assert recent[0].data_type == "type_14"  # most recent first

    def test_get_summary_empty(self):
        tracker = FallbackTracker()
        summary = tracker.get_summary()
        assert summary["total_events"] == 0
        assert summary["fallback_rate"] == 0.0

    def test_get_summary_with_events(self):
        tracker = FallbackTracker()

        # Event 1: no fallback
        tracker.begin("stock_list", "tushare")
        tracker.record_attempt("tushare", success=True, duration_ms=100.0)
        tracker.finish("tushare", success=True)

        # Event 2: fallback
        tracker.begin("kline", "tushare")
        tracker.record_attempt("tushare", success=False, duration_ms=200.0,
                               error="err", error_type="E")
        tracker.record_attempt("akshare", success=True, duration_ms=300.0)
        tracker.finish("akshare", success=True)

        # Event 3: all failed
        tracker.begin("news", "mongodb")
        tracker.record_attempt("mongodb", success=False, duration_ms=100.0,
                               error="err", error_type="E")
        tracker.record_attempt("tushare", success=False, duration_ms=200.0,
                               error="err", error_type="E")
        tracker.finish(None, success=False)

        summary = tracker.get_summary()
        assert summary["total_events"] == 3
        assert summary["fallback_count"] == 2  # events 2 and 3 had fallback
        assert summary["failure_count"] == 1  # event 3
        assert abs(summary["fallback_rate"] - 2/3) < 0.01

    def test_get_source_health(self):
        tracker = FallbackTracker()

        # tushare: 1 success, 1 failure
        tracker.begin("stock_list", "tushare")
        tracker.record_attempt("tushare", success=True, duration_ms=100.0)
        tracker.finish("tushare", success=True)

        tracker.begin("kline", "tushare")
        tracker.record_attempt("tushare", success=False, duration_ms=200.0,
                               error="err", error_type="E")
        tracker.record_attempt("akshare", success=True, duration_ms=300.0)
        tracker.finish("akshare", success=True)

        health = tracker.get_source_health()
        assert "tushare" in health
        assert health["tushare"]["attempts"] == 2
        assert health["tushare"]["successes"] == 1
        assert health["tushare"]["failures"] == 1
        assert health["tushare"]["success_rate"] == 0.5

    def test_thread_safety(self):
        """Test that the tracker is safe for concurrent use"""
        import threading
        tracker = FallbackTracker()
        errors = []

        def worker(n):
            try:
                for _ in range(10):
                    tracker.begin("test", "tushare")
                    tracker.record_attempt("tushare", success=True, duration_ms=10.0)
                    tracker.finish("tushare", success=True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(tracker.events) == 50


class TestSingleton:
    """Test get_fallback_tracker singleton"""

    def test_singleton_returns_same_instance(self):
        import app.services.data_sources.fallback_tracker as mod
        mod._instance = None
        t1 = get_fallback_tracker()
        t2 = get_fallback_tracker()
        assert t1 is t2
        mod._instance = None  # cleanup


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
