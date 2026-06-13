"""Concurrent request handling performance tests for TradingAgents-CN"""

import time
import asyncio
import pytest
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestConcurrentPerformance:
    """Test concurrent request handling performance"""

    def test_concurrent_health_checks(self, app_client, performance_timer, benchmark_result, performance_baseline):
        """Test concurrent health check requests"""
        num_requests = 10
        results = []

        with performance_timer as timer:
            with ThreadPoolExecutor(max_workers=num_requests) as executor:
                futures = [
                    executor.submit(app_client.get, "/api/health")
                    for _ in range(num_requests)
                ]
                for future in as_completed(futures):
                    try:
                        response = future.result()
                        results.append({
                            "status_code": response.status_code,
                            "success": response.status_code == 200
                        })
                    except Exception as e:
                        results.append({
                            "status_code": 0,
                            "success": False,
                            "error": str(e)
                        })

        success_count = sum(1 for r in results if r["success"])
        avg_time = timer.elapsed / num_requests

        benchmark_result("concurrent_health_10", timer.elapsed, {
            "total_requests": num_requests,
            "successful": success_count,
            "failed": num_requests - success_count,
            "average_time_per_request": round(avg_time, 4)
        })

        # At least 80% should succeed
        assert success_count >= num_requests * 0.8, \
            f"Only {success_count}/{num_requests} concurrent requests succeeded"

    def test_concurrent_mixed_endpoints(self, app_client, performance_timer, benchmark_result):
        """Test concurrent requests to different endpoints"""
        endpoints = [
            "/api/health",
            "/",
            "/api/health",
            "/",
            "/api/health",
        ]

        results = []

        with performance_timer as timer:
            with ThreadPoolExecutor(max_workers=len(endpoints)) as executor:
                futures = [
                    executor.submit(app_client.get, endpoint)
                    for endpoint in endpoints
                ]
                for future in as_completed(futures):
                    try:
                        response = future.result()
                        results.append({
                            "status_code": response.status_code,
                            "success": response.status_code == 200
                        })
                    except Exception as e:
                        results.append({
                            "status_code": 0,
                            "success": False,
                            "error": str(e)
                        })

        success_count = sum(1 for r in results if r["success"])

        benchmark_result("concurrent_mixed_endpoints", timer.elapsed, {
            "total_requests": len(endpoints),
            "successful": success_count,
            "failed": len(endpoints) - success_count
        })

    def test_concurrent_high_load(self, app_client, performance_timer, benchmark_result, performance_baseline):
        """Test system under higher concurrent load"""
        num_requests = 50
        results = []
        errors = []

        with performance_timer as timer:
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [
                    executor.submit(app_client.get, "/api/health")
                    for _ in range(num_requests)
                ]
                for future in as_completed(futures):
                    try:
                        response = future.result()
                        results.append({
                            "status_code": response.status_code,
                            "success": response.status_code == 200
                        })
                    except Exception as e:
                        errors.append(str(e))
                        results.append({
                            "status_code": 0,
                            "success": False,
                            "error": str(e)
                        })

        success_count = sum(1 for r in results if r["success"])
        avg_time = timer.elapsed / num_requests

        benchmark_result("concurrent_health_50", timer.elapsed, {
            "total_requests": num_requests,
            "successful": success_count,
            "failed": num_requests - success_count,
            "errors": errors[:5],  # Keep first 5 errors
            "average_time_per_request": round(avg_time, 4)
        })

        # System should handle at least 60% of requests under high load
        assert success_count >= num_requests * 0.6, \
            f"Only {success_count}/{num_requests} requests succeeded under high load"

    def test_concurrent_with_latency(self, app_client, performance_timer, benchmark_result):
        """Test concurrent requests with simulated latency"""
        num_requests = 10
        results = []

        def make_request_with_delay(delay: float):
            time.sleep(delay)
            return app_client.get("/api/health")

        with performance_timer as timer:
            with ThreadPoolExecutor(max_workers=num_requests) as executor:
                futures = [
                    executor.submit(make_request_with_delay, i * 0.01)
                    for i in range(num_requests)
                ]
                for future in as_completed(futures):
                    try:
                        response = future.result()
                        results.append({
                            "status_code": response.status_code,
                            "success": response.status_code == 200
                        })
                    except Exception as e:
                        results.append({
                            "status_code": 0,
                            "success": False,
                            "error": str(e)
                        })

        success_count = sum(1 for r in results if r["success"])

        benchmark_result("concurrent_with_latency", timer.elapsed, {
            "total_requests": num_requests,
            "successful": success_count,
            "failed": num_requests - success_count
        })

    def test_request_queue_handling(self, app_client, performance_timer, benchmark_result):
        """Test request queue handling under burst traffic"""
        burst_size = 20
        results = []
        start_times = []
        end_times = []

        with performance_timer as timer:
            with ThreadPoolExecutor(max_workers=burst_size) as executor:
                # Submit all requests at once (burst)
                futures = []
                for _ in range(burst_size):
                    start_times.append(time.perf_counter())
                    futures.append(executor.submit(app_client.get, "/api/health"))

                for future in as_completed(futures):
                    end_times.append(time.perf_counter())
                    try:
                        response = future.result()
                        results.append({
                            "status_code": response.status_code,
                            "success": response.status_code == 200
                        })
                    except Exception as e:
                        results.append({
                            "status_code": 0,
                            "success": False,
                            "error": str(e)
                        })

        success_count = sum(1 for r in results if r["success"])

        # Calculate request spread (time between first and last completion)
        if end_times:
            request_spread = max(end_times) - min(end_times)
        else:
            request_spread = 0

        benchmark_result("request_queue_burst", timer.elapsed, {
            "burst_size": burst_size,
            "successful": success_count,
            "failed": burst_size - success_count,
            "request_spread_seconds": round(request_spread, 4)
        })

    def test_sequential_vs_concurrent(self, app_client, performance_timer, benchmark_result):
        """Compare sequential vs concurrent request performance"""
        num_requests = 10

        # Sequential requests
        with performance_timer as seq_timer:
            for _ in range(num_requests):
                response = app_client.get("/api/health")
                assert response.status_code == 200

        # Concurrent requests
        with performance_timer as con_timer:
            with ThreadPoolExecutor(max_workers=num_requests) as executor:
                futures = [
                    executor.submit(app_client.get, "/api/health")
                    for _ in range(num_requests)
                ]
                for future in as_completed(futures):
                    response = future.result()
                    assert response.status_code == 200

        speedup = seq_timer.elapsed / con_timer.elapsed if con_timer.elapsed > 0 else float('inf')

        benchmark_result("sequential_vs_concurrent", con_timer.elapsed, {
            "sequential_time": round(seq_timer.elapsed, 4),
            "concurrent_time": round(con_timer.elapsed, 4),
            "speedup_factor": round(speedup, 2)
        })
