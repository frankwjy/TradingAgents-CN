"""
Data source fallback transparency tracker.

Records every fallback attempt with structured data, generates summary logs,
and exposes health metrics for the API layer.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FallbackAttempt:
    """One try against a single data source."""
    source_name: str
    success: bool
    duration_ms: float
    error: Optional[str] = None
    error_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error,
            "error_type": self.error_type,
        }


@dataclass
class FallbackEvent:
    """A complete fallback sequence for one data-type fetch."""
    data_type: str
    primary_source: str
    final_source: Optional[str]
    success: bool
    total_duration_ms: float
    attempts: List[FallbackAttempt] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    symbol: Optional[str] = None

    @property
    def fallback_count(self) -> int:
        """Number of sources tried after the primary."""
        return max(0, len(self.attempts) - 1)

    @property
    def fallback_chain(self) -> List[str]:
        """Ordered list of all source names that were attempted."""
        return [a.source_name for a in self.attempts]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_type": self.data_type,
            "symbol": self.symbol,
            "primary_source": self.primary_source,
            "final_source": self.final_source,
            "success": self.success,
            "fallback_count": self.fallback_count,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "fallback_chain": self.fallback_chain,
            "attempts": [a.to_dict() for a in self.attempts],
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

class FallbackTracker:
    """Thread-safe tracker for data source fallback events."""

    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.events: List[FallbackEvent] = []
        self._current_event: Optional[FallbackEvent] = None
        self._start_time: float = 0.0

    # -- lifecycle --

    def begin(self, data_type: str, primary_source: str, symbol: Optional[str] = None) -> None:
        """Start tracking a new fallback sequence."""
        with self._lock:
            self._current_event = FallbackEvent(
                data_type=data_type,
                primary_source=primary_source,
                final_source=None,
                success=False,
                total_duration_ms=0.0,
                symbol=symbol,
            )
            self._start_time = time.monotonic()

    def record_attempt(
        self,
        source_name: str,
        success: bool,
        duration_ms: float,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
    ) -> None:
        """Record a single source attempt within the current sequence."""
        with self._lock:
            if self._current_event is None:
                return
            self._current_event.attempts.append(FallbackAttempt(
                source_name=source_name,
                success=success,
                duration_ms=duration_ms,
                error=error,
                error_type=error_type,
            ))

    def finish(self, final_source: Optional[str], success: bool) -> FallbackEvent:
        """Complete the current sequence and store the event."""
        with self._lock:
            if self._current_event is None:
                return FallbackEvent(
                    data_type="unknown",
                    primary_source="unknown",
                    final_source=final_source,
                    success=success,
                    total_duration_ms=0.0,
                )
            self._current_event.final_source = final_source
            self._current_event.success = success
            self._current_event.total_duration_ms = (
                (time.monotonic() - self._start_time) * 1000
            )
            event = self._current_event
            self._current_event = None

            self.events.append(event)
            if len(self.events) > self._MAX_EVENTS:
                self.events = self.events[-self._MAX_EVENTS:]

            self._log_event(event)
            return event

    # -- queries --

    def recent_events(self, limit: int = 20) -> List[FallbackEvent]:
        """Return the most recent events (newest first)."""
        with self._lock:
            return list(reversed(self.events[-limit:]))

    def get_summary(self) -> Dict[str, Any]:
        """Aggregate summary across all tracked events."""
        with self._lock:
            total = len(self.events)
            if total == 0:
                return {
                    "total_events": 0,
                    "fallback_count": 0,
                    "failure_count": 0,
                    "fallback_rate": 0.0,
                    "failure_rate": 0.0,
                    "avg_duration_ms": 0.0,
                    "by_data_type": {},
                }

            fallback_count = sum(1 for e in self.events if e.fallback_count > 0)
            failure_count = sum(1 for e in self.events if not e.success)
            total_duration = sum(e.total_duration_ms for e in self.events)

            by_type: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
                "total": 0, "fallback": 0, "failed": 0,
            })
            for e in self.events:
                bt = by_type[e.data_type]
                bt["total"] += 1
                if e.fallback_count > 0:
                    bt["fallback"] += 1
                if not e.success:
                    bt["failed"] += 1

            return {
                "total_events": total,
                "fallback_count": fallback_count,
                "failure_count": failure_count,
                "fallback_rate": round(fallback_count / total, 4),
                "failure_rate": round(failure_count / total, 4),
                "avg_duration_ms": round(total_duration / total, 2),
                "by_data_type": dict(by_type),
            }

    def get_source_health(self) -> Dict[str, Dict[str, Any]]:
        """Per-source success/failure statistics."""
        with self._lock:
            stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
                "attempts": 0, "successes": 0, "failures": 0,
                "total_duration_ms": 0.0, "errors": [],
            })
            for e in self.events:
                for a in e.attempts:
                    s = stats[a.source_name]
                    s["attempts"] += 1
                    s["total_duration_ms"] += a.duration_ms
                    if a.success:
                        s["successes"] += 1
                    else:
                        s["failures"] += 1
                        if a.error:
                            s["errors"].append(a.error)

            result = {}
            for name, s in stats.items():
                attempts = s["attempts"]
                result[name] = {
                    "attempts": attempts,
                    "successes": s["successes"],
                    "failures": s["failures"],
                    "success_rate": round(s["successes"] / attempts, 4) if attempts else 0.0,
                    "avg_duration_ms": round(s["total_duration_ms"] / attempts, 2) if attempts else 0.0,
                    "recent_errors": s["errors"][-5:],
                }
            return result

    # -- internal --

    def _log_event(self, event: FallbackEvent) -> None:
        """Log the fallback event with structured data."""
        if event.fallback_count > 0:
            chain_str = " -> ".join(event.fallback_chain)
            if event.success:
                logger.warning(
                    f"⚠️ [数据源回退] {event.data_type} | "
                    f"主数据源={event.primary_source} 失败, "
                    f"回退链={chain_str}, "
                    f"最终使用={event.final_source}, "
                    f"耗时={event.total_duration_ms:.0f}ms",
                    extra={
                        "event_type": "datasource_fallback",
                        "data_type": event.data_type,
                        "symbol": event.symbol,
                        "primary_source": event.primary_source,
                        "final_source": event.final_source,
                        "fallback_count": event.fallback_count,
                        "fallback_chain": event.fallback_chain,
                        "total_duration_ms": round(event.total_duration_ms, 2),
                        "success": event.success,
                    },
                )
            else:
                error_msgs = [
                    f"{a.source_name}: {a.error or 'unknown'}"
                    for a in event.attempts if not a.success
                ]
                logger.error(
                    f"❌ [数据源回退失败] {event.data_type} | "
                    f"所有数据源均失败, 回退链={chain_str}, "
                    f"错误={'; '.join(error_msgs)}, "
                    f"耗时={event.total_duration_ms:.0f}ms",
                    extra={
                        "event_type": "datasource_fallback_all_failed",
                        "data_type": event.data_type,
                        "symbol": event.symbol,
                        "primary_source": event.primary_source,
                        "fallback_chain": event.fallback_chain,
                        "errors": error_msgs,
                        "total_duration_ms": round(event.total_duration_ms, 2),
                    },
                )
        elif not event.success:
            logger.error(
                f"❌ [数据源失败] {event.data_type} | "
                f"数据源={event.primary_source} 失败, 无可用回退, "
                f"耗时={event.total_duration_ms:.0f}ms",
                extra={
                    "event_type": "datasource_failure_no_fallback",
                    "data_type": event.data_type,
                    "symbol": event.symbol,
                    "source": event.primary_source,
                    "total_duration_ms": round(event.total_duration_ms, 2),
                },
            )
        else:
            logger.debug(
                f"✅ [数据源成功] {event.data_type} | "
                f"数据源={event.primary_source}, "
                f"耗时={event.total_duration_ms:.0f}ms",
            )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_instance: Optional[FallbackTracker] = None
_init_lock = threading.Lock()


def get_fallback_tracker() -> FallbackTracker:
    """Return the process-wide FallbackTracker singleton."""
    global _instance
    if _instance is None:
        with _init_lock:
            if _instance is None:
                _instance = FallbackTracker()
    return _instance
