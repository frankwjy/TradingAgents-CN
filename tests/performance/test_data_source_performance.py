"""Data source adapter performance tests for TradingAgents-CN"""

import time
import pytest
from typing import Dict, Any, Optional


class TestDataSourcePerformance:
    """Test data source adapter performance"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup data source adapters"""
        self.adapters = {}
        try:
            # Try to import and create individual adapters directly
            from app.services.data_sources.akshare_adapter import AKShareAdapter
            from app.services.data_sources.baostock_adapter import BaoStockAdapter

            # Test each adapter individually
            try:
                akshare = AKShareAdapter()
                self.adapters['akshare'] = akshare
            except Exception:
                pass

            try:
                baostock = BaoStockAdapter()
                self.adapters['baostock'] = baostock
            except Exception:
                pass

            if not self.adapters:
                pytest.skip("No data source adapters available")

        except ImportError as e:
            pytest.skip(f"Could not import data source adapters: {e}")
        except Exception as e:
            pytest.skip(f"Could not initialize data source manager: {e}")

    def test_akshare_availability(self, performance_timer, benchmark_result):
        """Test AKShare adapter availability and response time"""
        if 'akshare' not in self.adapters:
            pytest.skip("AKShare adapter not available")

        adapter = self.adapters['akshare']

        with performance_timer as timer:
            is_available = adapter.is_available()

        benchmark_result("data_source_akshare_availability", timer.elapsed, {
            "available": is_available
        })

    def test_akshare_stock_list_performance(self, performance_timer, benchmark_result, performance_baseline):
        """Test AKShare stock list retrieval performance"""
        if 'akshare' not in self.adapters:
            pytest.skip("AKShare adapter not available")

        adapter = self.adapters['akshare']

        with performance_timer as timer:
            try:
                stock_list = adapter.get_stock_list()
                success = stock_list is not None and not stock_list.empty
                record_count = len(stock_list) if success else 0
            except Exception as e:
                success = False
                record_count = 0

        benchmark_result("data_source_akshare_stock_list", timer.elapsed, {
            "success": success,
            "record_count": record_count
        })

        if success:
            assert timer.elapsed <= performance_baseline["data_source_akshare_stock_list"], \
                f"AKShare stock list took {timer.elapsed:.2f}s, exceeding threshold"

    def test_baostock_availability(self, performance_timer, benchmark_result):
        """Test BaoStock adapter availability and response time"""
        if 'baostock' not in self.adapters:
            pytest.skip("BaoStock adapter not available")

        adapter = self.adapters['baostock']

        with performance_timer as timer:
            is_available = adapter.is_available()

        benchmark_result("data_source_baostock_availability", timer.elapsed, {
            "available": is_available
        })

    def test_baostock_stock_list_performance(self, performance_timer, benchmark_result, performance_baseline):
        """Test BaoStock stock list retrieval performance"""
        if 'baostock' not in self.adapters:
            pytest.skip("BaoStock adapter not available")

        adapter = self.adapters['baostock']

        with performance_timer as timer:
            try:
                stock_list = adapter.get_stock_list()
                success = stock_list is not None and not stock_list.empty
                record_count = len(stock_list) if success else 0
            except Exception as e:
                success = False
                record_count = 0

        benchmark_result("data_source_baostock_stock_list", timer.elapsed, {
            "success": success,
            "record_count": record_count
        })

        if success:
            assert timer.elapsed <= performance_baseline["data_source_baostock_stock_list"], \
                f"BaoStock stock list took {timer.elapsed:.2f}s, exceeding threshold"

    def test_tushare_availability(self, performance_timer, benchmark_result):
        """Test Tushare adapter availability and response time"""
        if 'tushare' not in self.adapters:
            pytest.skip("Tushare adapter not available")

        adapter = self.adapters['tushare']

        with performance_timer as timer:
            is_available = adapter.is_available()

        benchmark_result("data_source_tushare_availability", timer.elapsed, {
            "available": is_available
        })

    def test_data_source_comparison(self, performance_timer, benchmark_result):
        """Compare performance across available data sources"""
        results = {}

        for name, adapter in self.adapters.items():
            with performance_timer as timer:
                try:
                    is_available = adapter.is_available()
                    if is_available:
                        stock_list = adapter.get_stock_list()
                        success = stock_list is not None and not stock_list.empty
                    else:
                        success = False
                except Exception:
                    success = False

            results[name] = {
                "available": is_available if 'is_available' in dir() else False,
                "success": success,
                "elapsed": round(timer.elapsed, 4)
            }

        benchmark_result("data_source_comparison", sum(r["elapsed"] for r in results.values()), {
            "sources": results
        })

    def test_data_source_error_handling(self, performance_timer, benchmark_result):
        """Test data source error handling performance"""
        if not self.adapters:
            pytest.skip("No data source adapters available")

        results = {}
        for name, adapter in self.adapters.items():
            with performance_timer as timer:
                try:
                    # Try to get data for an invalid stock code
                    result = adapter.get_daily_basic("invalid_code_12345")
                    error_handled = True
                except Exception:
                    error_handled = True

            results[name] = {
                "error_handling_time": round(timer.elapsed, 4),
                "handled": error_handled
            }

        benchmark_result("data_source_error_handling", sum(r["error_handling_time"] for r in results.values()), {
            "sources": results
        })
