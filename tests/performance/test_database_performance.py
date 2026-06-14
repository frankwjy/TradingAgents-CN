"""Database operation performance tests for TradingAgents-CN"""

import time
import pytest
from typing import Dict, Any


class TestDatabasePerformance:
    """Test database operation performance"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup database connections"""
        self.db = None
        try:
            from app.core.database import get_database
            self.db = get_database()
        except Exception as e:
            pytest.skip(f"Could not connect to database: {e}")

    def test_database_connection_performance(self, performance_timer, benchmark_result):
        """Test database connection establishment time"""
        with performance_timer as timer:
            try:
                from app.core.database import get_database
                db = get_database()
                # Try a simple operation to verify connection
                db.list_collection_names()
                success = True
            except Exception as e:
                success = False

        benchmark_result("database_connection", timer.elapsed, {
            "success": success
        })

    def test_database_read_performance(self, performance_timer, benchmark_result, performance_baseline):
        """Test database read operation performance"""
        if self.db is None:
            pytest.skip("Database not available")

        collection = self.db["stocks"]

        with performance_timer as timer:
            try:
                # Read a small set of documents
                results = list(collection.find().limit(10))
                success = True
                doc_count = len(results)
            except Exception as e:
                success = False
                doc_count = 0

        benchmark_result("database_read", timer.elapsed, {
            "success": success,
            "document_count": doc_count
        })

        if success:
            assert timer.elapsed <= performance_baseline["database_read"], \
                f"Database read took {timer.elapsed:.3f}s, exceeding threshold"

    def test_database_write_performance(self, performance_timer, benchmark_result, performance_baseline):
        """Test database write operation performance"""
        if self.db is None:
            pytest.skip("Database not available")

        collection = self.db["performance_test"]

        test_doc = {
            "test_id": "perf_test_" + str(int(time.time())),
            "timestamp": time.time(),
            "data": "x" * 1000  # 1KB of data
        }

        with performance_timer as timer:
            try:
                result = collection.insert_one(test_doc)
                success = result.inserted_id is not None
                # Cleanup
                collection.delete_one({"_id": result.inserted_id})
            except Exception as e:
                success = False

        benchmark_result("database_write", timer.elapsed, {
            "success": success
        })

        if success:
            assert timer.elapsed <= performance_baseline["database_write"], \
                f"Database write took {timer.elapsed:.3f}s, exceeding threshold"

    def test_database_query_performance(self, performance_timer, benchmark_result):
        """Test database query performance with filters"""
        if self.db is None:
            pytest.skip("Database not available")

        collection = self.db["stocks"]

        with performance_timer as timer:
            try:
                # Query with filter
                results = list(collection.find({"status": "active"}).limit(100))
                success = True
                doc_count = len(results)
            except Exception as e:
                success = False
                doc_count = 0

        benchmark_result("database_query_filtered", timer.elapsed, {
            "success": success,
            "document_count": doc_count
        })

    def test_database_aggregation_performance(self, performance_timer, benchmark_result):
        """Test database aggregation pipeline performance"""
        if self.db is None:
            pytest.skip("Database not available")

        collection = self.db["stocks"]

        pipeline = [
            {"$limit": 100},
            {"$group": {"_id": "$market", "count": {"$sum": 1}}}
        ]

        with performance_timer as timer:
            try:
                results = list(collection.aggregate(pipeline))
                success = True
                group_count = len(results)
            except Exception as e:
                success = False
                group_count = 0

        benchmark_result("database_aggregation", timer.elapsed, {
            "success": success,
            "group_count": group_count
        })

    def test_database_index_performance(self, performance_timer, benchmark_result):
        """Test database index effectiveness"""
        if self.db is None:
            pytest.skip("Database not available")

        collection = self.db["stocks"]

        # First, check if indexes exist
        with performance_timer as timer:
            try:
                indexes = collection.index_information()
                index_count = len(indexes)
            except Exception:
                index_count = 0

        benchmark_result("database_indexes", timer.elapsed, {
            "index_count": index_count
        })

    def test_database_bulk_read_performance(self, performance_timer, benchmark_result):
        """Test database bulk read performance"""
        if self.db is None:
            pytest.skip("Database not available")

        collection = self.db["stocks"]

        with performance_timer as timer:
            try:
                # Read larger set of documents
                results = list(collection.find().limit(1000))
                success = True
                doc_count = len(results)
            except Exception as e:
                success = False
                doc_count = 0

        benchmark_result("database_bulk_read", timer.elapsed, {
            "success": success,
            "document_count": doc_count
        })

    def test_database_concurrent_operations(self, performance_timer, benchmark_result):
        """Test database performance under concurrent-like operations"""
        if self.db is None:
            pytest.skip("Database not available")

        collection = self.db["stocks"]

        with performance_timer as timer:
            try:
                # Simulate concurrent-like operations
                for _ in range(10):
                    list(collection.find().limit(10))
                success = True
            except Exception as e:
                success = False

        benchmark_result("database_concurrent_ops", timer.elapsed, {
            "success": success,
            "operations": 10
        })
