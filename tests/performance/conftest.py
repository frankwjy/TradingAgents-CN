"""Performance test fixtures for TradingAgents-CN"""

import os
import sys
import time
import json
import pytest
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope="session")
def performance_baseline():
    """Load or create performance baseline metrics"""
    baseline_path = Path(__file__).parent / "performance_baseline.json"

    if baseline_path.exists():
        with open(baseline_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Default baseline thresholds (in seconds)
    return {
        "api_health_check": 0.5,
        "api_stock_list": 2.0,
        "api_stock_detail": 1.0,
        "api_analysis_start": 5.0,
        "api_screening": 3.0,
        "data_source_akshare_stock_list": 10.0,
        "data_source_akshare_daily": 15.0,
        "data_source_baostock_stock_list": 10.0,
        "database_read": 0.5,
        "database_write": 1.0,
        "cache_read": 0.1,
        "cache_write": 0.2,
        "concurrent_requests_10": 10.0,
        "concurrent_requests_50": 30.0,
    }


@pytest.fixture(scope="session")
def performance_results():
    """Collect performance results throughout the session"""
    results = {}
    yield results

    # Save results at end of session
    results_path = Path(__file__).parent / "performance_results.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


@pytest.fixture
def performance_timer():
    """Context manager for timing operations"""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end_time = time.perf_counter()
            self.elapsed = self.end_time - self.start_time

        def assert_within_threshold(self, threshold: float, operation_name: str = "Operation"):
            """Assert that the operation completed within the threshold"""
            assert self.elapsed is not None, "Timer not completed"
            assert self.elapsed <= threshold, \
                f"{operation_name} took {self.elapsed:.3f}s, exceeding threshold of {threshold}s"

    return Timer()


@pytest.fixture
def benchmark_result(performance_results):
    """Fixture to record benchmark results"""
    def _record(test_name: str, elapsed: float, details: Optional[Dict[str, Any]] = None):
        performance_results[test_name] = {
            "elapsed_seconds": round(elapsed, 4),
            "details": details or {},
            "passed": True
        }
        return elapsed
    return _record


@pytest.fixture(scope="session")
def app_client():
    """Create a test client for the FastAPI application"""
    try:
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        yield client
    except Exception as e:
        pytest.skip(f"Could not create test client: {e}")


@pytest.fixture(scope="session")
def async_app_client():
    """Create an async test client for the FastAPI application"""
    try:
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async def _create_client():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client

        return _create_client()
    except Exception as e:
        pytest.skip(f"Could not create async test client: {e}")
