"""Cache operation performance tests for TradingAgents-CN"""

import time
import json
import pytest
from typing import Dict, Any


class TestCachePerformance:
    """Test cache operation performance"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup Redis connection"""
        self.redis_client = None
        try:
            from app.core.redis_client import get_redis
            self.redis_client = get_redis()
            if self.redis_client:
                self.redis_client.ping()
        except Exception as e:
            pytest.skip(f"Could not connect to Redis: {e}")

    def test_cache_connection_performance(self, performance_timer, benchmark_result):
        """Test cache connection establishment time"""
        with performance_timer as timer:
            try:
                from app.core.redis_client import get_redis
                redis_client = get_redis()
                if redis_client:
                    redis_client.ping()
                    success = True
                else:
                    success = False
            except Exception:
                success = False

        benchmark_result("cache_connection", timer.elapsed, {
            "success": success
        })

    def test_cache_write_performance(self, performance_timer, benchmark_result, performance_baseline):
        """Test cache write operation performance"""
        if self.redis_client is None:
            pytest.skip("Redis not available")

        test_key = f"perf_test_{int(time.time())}"
        test_value = json.dumps({"data": "x" * 1000, "timestamp": time.time()})

        with performance_timer as timer:
            try:
                self.redis_client.setex(test_key, 60, test_value)
                success = True
            except Exception as e:
                success = False
            finally:
                # Cleanup
                try:
                    self.redis_client.delete(test_key)
                except Exception:
                    pass

        benchmark_result("cache_write", timer.elapsed, {
            "success": success
        })

        if success:
            assert timer.elapsed <= performance_baseline["cache_write"], \
                f"Cache write took {timer.elapsed:.4f}s, exceeding threshold"

    def test_cache_read_performance(self, performance_timer, benchmark_result, performance_baseline):
        """Test cache read operation performance"""
        if self.redis_client is None:
            pytest.skip("Redis not available")

        test_key = f"perf_test_read_{int(time.time())}"
        test_value = json.dumps({"data": "test_data", "timestamp": time.time()})

        # Setup
        self.redis_client.setex(test_key, 60, test_value)

        with performance_timer as timer:
            try:
                result = self.redis_client.get(test_key)
                success = result is not None
            except Exception as e:
                success = False
            finally:
                # Cleanup
                try:
                    self.redis_client.delete(test_key)
                except Exception:
                    pass

        benchmark_result("cache_read", timer.elapsed, {
            "success": success
        })

        if success:
            assert timer.elapsed <= performance_baseline["cache_read"], \
                f"Cache read took {timer.elapsed:.4f}s, exceeding threshold"

    def test_cache_batch_write_performance(self, performance_timer, benchmark_result):
        """Test cache batch write performance"""
        if self.redis_client is None:
            pytest.skip("Redis not available")

        test_keys = [f"perf_batch_{i}_{int(time.time())}" for i in range(100)]
        test_value = json.dumps({"data": "batch_test"})

        with performance_timer as timer:
            try:
                pipe = self.redis_client.pipeline()
                for key in test_keys:
                    pipe.setex(key, 60, test_value)
                pipe.execute()
                success = True
            except Exception as e:
                success = False
            finally:
                # Cleanup
                try:
                    self.redis_client.delete(*test_keys)
                except Exception:
                    pass

        benchmark_result("cache_batch_write", timer.elapsed, {
            "success": success,
            "batch_size": 100
        })

    def test_cache_batch_read_performance(self, performance_timer, benchmark_result):
        """Test cache batch read performance"""
        if self.redis_client is None:
            pytest.skip("Redis not available")

        test_keys = [f"perf_batch_read_{i}_{int(time.time())}" for i in range(100)]
        test_value = json.dumps({"data": "batch_read_test"})

        # Setup
        pipe = self.redis_client.pipeline()
        for key in test_keys:
            pipe.setex(key, 60, test_value)
        pipe.execute()

        with performance_timer as timer:
            try:
                pipe = self.redis_client.pipeline()
                for key in test_keys:
                    pipe.get(key)
                results = pipe.execute()
                success = all(r is not None for r in results)
            except Exception as e:
                success = False
            finally:
                # Cleanup
                try:
                    self.redis_client.delete(*test_keys)
                except Exception:
                    pass

        benchmark_result("cache_batch_read", timer.elapsed, {
            "success": success,
            "batch_size": 100
        })

    def test_cache_delete_performance(self, performance_timer, benchmark_result):
        """Test cache delete operation performance"""
        if self.redis_client is None:
            pytest.skip("Redis not available")

        test_key = f"perf_delete_{int(time.time())}"
        test_value = json.dumps({"data": "delete_test"})
        self.redis_client.setex(test_key, 60, test_value)

        with performance_timer as timer:
            try:
                self.redis_client.delete(test_key)
                success = True
            except Exception as e:
                success = False

        benchmark_result("cache_delete", timer.elapsed, {
            "success": success
        })

    def test_cache_key_pattern_performance(self, performance_timer, benchmark_result):
        """Test cache key pattern matching performance"""
        if self.redis_client is None:
            pytest.skip("Redis not available")

        # Create test keys
        test_prefix = f"perf_pattern_{int(time.time())}_"
        test_keys = [f"{test_prefix}{i}" for i in range(50)]
        test_value = json.dumps({"data": "pattern_test"})

        pipe = self.redis_client.pipeline()
        for key in test_keys:
            pipe.setex(key, 60, test_value)
        pipe.execute()

        with performance_timer as timer:
            try:
                # Use SCAN for pattern matching
                cursor = 0
                matched_keys = []
                while True:
                    cursor, keys = self.redis_client.scan(cursor, match=f"{test_prefix}*", count=100)
                    matched_keys.extend(keys)
                    if cursor == 0:
                        break
                success = len(matched_keys) == len(test_keys)
            except Exception as e:
                success = False
            finally:
                # Cleanup
                try:
                    self.redis_client.delete(*test_keys)
                except Exception:
                    pass

        benchmark_result("cache_pattern_match", timer.elapsed, {
            "success": success,
            "matched_count": len(matched_keys) if 'matched_keys' in dir() else 0
        })

    def test_cache_expiration_performance(self, performance_timer, benchmark_result):
        """Test cache TTL operation performance"""
        if self.redis_client is None:
            pytest.skip("Redis not available")

        test_key = f"perf_ttl_{int(time.time())}"
        test_value = json.dumps({"data": "ttl_test"})
        self.redis_client.setex(test_key, 60, test_value)

        with performance_timer as timer:
            try:
                ttl = self.redis_client.ttl(test_key)
                success = ttl > 0
            except Exception as e:
                success = False
            finally:
                # Cleanup
                try:
                    self.redis_client.delete(test_key)
                except Exception:
                    pass

        benchmark_result("cache_ttl", timer.elapsed, {
            "success": success,
            "ttl": ttl if 'ttl' in dir() else -1
        })
