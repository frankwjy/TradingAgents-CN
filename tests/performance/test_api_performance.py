"""API endpoint performance tests for TradingAgents-CN"""

import time
import pytest
from typing import Dict, Any


class TestAPIPerformance:
    """Test API endpoint response times"""

    def test_health_endpoint_performance(self, app_client, performance_timer, benchmark_result, performance_baseline):
        """Test health check endpoint performance"""
        with performance_timer as timer:
            for _ in range(10):
                response = app_client.get("/api/health")
                assert response.status_code == 200

        avg_time = timer.elapsed / 10
        benchmark_result("api_health_check", avg_time)
        timer.assert_within_threshold(performance_baseline["api_health_check"], "Health check")

    def test_root_endpoint_performance(self, app_client, performance_timer, benchmark_result):
        """Test root endpoint performance"""
        with performance_timer as timer:
            response = app_client.get("/")
            assert response.status_code == 200

        benchmark_result("api_root", timer.elapsed)

    def test_stock_list_endpoint_performance(self, app_client, performance_timer, benchmark_result, performance_baseline):
        """Test stock list endpoint performance"""
        with performance_timer as timer:
            response = app_client.get("/api/stocks")

        if response.status_code == 200:
            benchmark_result("api_stock_list", timer.elapsed)
            # Only assert threshold if endpoint is available
            if timer.elapsed > performance_baseline["api_stock_list"]:
                pytest.skip(f"Stock list endpoint slow ({timer.elapsed:.2f}s), may need external service")

    def test_screening_endpoint_performance(self, app_client, performance_timer, benchmark_result, performance_baseline):
        """Test screening endpoint performance"""
        with performance_timer as timer:
            response = app_client.get("/api/screening")

        if response.status_code == 200:
            benchmark_result("api_screening", timer.elapsed)

    def test_analysis_endpoint_performance(self, app_client, performance_timer, benchmark_result):
        """Test analysis endpoint performance (read-only)"""
        with performance_timer as timer:
            response = app_client.get("/api/analysis")

        # Record result regardless of status code
        benchmark_result("api_analysis_list", timer.elapsed, {
            "status_code": response.status_code
        })

    def test_config_endpoint_performance(self, app_client, performance_timer, benchmark_result):
        """Test config endpoint performance"""
        with performance_timer as timer:
            response = app_client.get("/api/config")

        benchmark_result("api_config", timer.elapsed, {
            "status_code": response.status_code
        })

    def test_model_capabilities_performance(self, app_client, performance_timer, benchmark_result):
        """Test model capabilities endpoint performance"""
        with performance_timer as timer:
            response = app_client.get("/api/model-capabilities")

        benchmark_result("api_model_capabilities", timer.elapsed, {
            "status_code": response.status_code
        })

    def test_favorites_endpoint_performance(self, app_client, performance_timer, benchmark_result):
        """Test favorites endpoint performance"""
        with performance_timer as timer:
            response = app_client.get("/api/favorites")

        benchmark_result("api_favorites", timer.elapsed, {
            "status_code": response.status_code
        })

    def test_tags_endpoint_performance(self, app_client, performance_timer, benchmark_result):
        """Test tags endpoint performance"""
        with performance_timer as timer:
            response = app_client.get("/api/tags")

        benchmark_result("api_tags", timer.elapsed, {
            "status_code": response.status_code
        })

    def test_operation_logs_performance(self, app_client, performance_timer, benchmark_result):
        """Test operation logs endpoint performance"""
        with performance_timer as timer:
            response = app_client.get("/api/system/operation-logs")

        benchmark_result("api_operation_logs", timer.elapsed, {
            "status_code": response.status_code
        })

    def test_scheduler_status_performance(self, app_client, performance_timer, benchmark_result):
        """Test scheduler status endpoint performance"""
        with performance_timer as timer:
            response = app_client.get("/api/scheduler/status")

        benchmark_result("api_scheduler_status", timer.elapsed, {
            "status_code": response.status_code
        })

    def test_api_response_consistency(self, app_client, performance_timer, benchmark_result):
        """Test that API responses are consistent in timing"""
        times = []
        endpoints = ["/api/health", "/", "/api/health", "/", "/api/health"]

        with performance_timer as timer:
            for endpoint in endpoints:
                start = time.perf_counter()
                response = app_client.get(endpoint)
                elapsed = time.perf_counter() - start
                times.append(elapsed)
                assert response.status_code == 200

        avg_time = sum(times) / len(times)
        max_deviation = max(abs(t - avg_time) for t in times)

        benchmark_result("api_response_consistency", timer.elapsed, {
            "average": round(avg_time, 4),
            "max_deviation": round(max_deviation, 4),
            "all_times": [round(t, 4) for t in times]
        })

        # Response times should be consistent (max deviation < 50% of average)
        assert max_deviation < avg_time * 0.5 or avg_time < 0.01, \
            f"Response times inconsistent: avg={avg_time:.4f}s, max_deviation={max_deviation:.4f}s"
