"""
数据源回退机制测试
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from tradingagents.dataflows.providers.china.data_source_fallback import (
    DataSourceFallback,
    DataSourcePriority,
    DataSourceConfig,
    StockQuotesFallback,
    StockNewsFallback,
    StockListFallback,
)


class TestDataSourceFallback:
    """数据源回退管理器测试"""

    def setup_method(self):
        """测试前重置状态"""
        self.fallback = DataSourceFallback("test")

    def test_add_source(self):
        """测试添加数据源"""
        mock_func = Mock(return_value="data")
        self.fallback.add_source("source1", mock_func, DataSourcePriority.PRIMARY)

        assert "source1" in self.fallback._sources
        assert self.fallback._sources["source1"].priority == DataSourcePriority.PRIMARY

    def test_get_available_sources(self):
        """测试获取可用数据源"""
        mock_func1 = Mock(return_value="data1")
        mock_func2 = Mock(return_value="data2")

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        available = self.fallback.get_available_sources()
        assert len(available) == 2
        assert "source1" in available
        assert "source2" in available

    def test_mark_error(self):
        """测试标记错误"""
        mock_func = Mock(return_value="data")
        self.fallback.add_source("source1", mock_func, DataSourcePriority.PRIMARY)

        # 标记错误
        self.fallback.mark_error("source1", "Test error")
        assert self.fallback._sources["source1"].error_count == 1
        assert self.fallback._sources["source1"].last_error == "Test error"
        assert self.fallback._sources["source1"].available is True

    def test_mark_error_max_errors(self):
        """测试错误次数超过最大值"""
        mock_func = Mock(return_value="data")
        self.fallback.add_source("source1", mock_func, DataSourcePriority.PRIMARY, max_errors=2)

        # 标记错误超过最大值
        self.fallback.mark_error("source1", "Error 1")
        self.fallback.mark_error("source1", "Error 2")

        assert self.fallback._sources["source1"].error_count == 2
        assert self.fallback._sources["source1"].available is False

    def test_mark_success(self):
        """测试标记成功"""
        mock_func = Mock(return_value="data")
        self.fallback.add_source("source1", mock_func, DataSourcePriority.PRIMARY)

        # 先标记错误
        self.fallback.mark_error("source1", "Test error")
        assert self.fallback._sources["source1"].error_count == 1

        # 再标记成功
        self.fallback.mark_success("source1")
        assert self.fallback._sources["source1"].error_count == 0
        assert self.fallback._sources["source1"].last_error is None
        assert self.fallback._sources["source1"].available is True

    def test_reset_all(self):
        """测试重置所有数据源"""
        mock_func1 = Mock(return_value="data1")
        mock_func2 = Mock(return_value="data2")

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        # 标记错误
        self.fallback.mark_error("source1", "Error 1")
        self.fallback.mark_error("source2", "Error 2")

        # 重置所有
        self.fallback.reset_all()

        assert self.fallback._sources["source1"].error_count == 0
        assert self.fallback._sources["source2"].error_count == 0
        assert self.fallback._sources["source1"].available is True
        assert self.fallback._sources["source2"].available is True

    def test_fetch_with_fallback_success_first_source(self):
        """测试第一次数据源就成功"""
        mock_func1 = Mock(return_value="data1")
        mock_func2 = Mock(return_value="data2")

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        result = self.fallback.fetch_with_fallback()
        assert result == "data1"
        mock_func1.assert_called_once()
        mock_func2.assert_not_called()

    def test_fetch_with_fallback_success_second_source(self):
        """测试第一次数据源失败，第二次成功"""
        mock_func1 = Mock(side_effect=Exception("Source 1 failed"))
        mock_func2 = Mock(return_value="data2")

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        result = self.fallback.fetch_with_fallback()
        assert result == "data2"
        mock_func1.assert_called_once()
        mock_func2.assert_called_once()

    def test_fetch_with_fallback_all_fail(self):
        """测试所有数据源都失败"""
        mock_func1 = Mock(side_effect=Exception("Source 1 failed"))
        mock_func2 = Mock(side_effect=Exception("Source 2 failed"))

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        with pytest.raises(Exception) as exc_info:
            self.fallback.fetch_with_fallback()

        assert "Source 2 failed" in str(exc_info.value)

    def test_fetch_with_fallback_preferred_source(self):
        """测试指定首选数据源"""
        mock_func1 = Mock(return_value="data1")
        mock_func2 = Mock(return_value="data2")

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        result = self.fallback.fetch_with_fallback(preferred_source="source2")
        assert result == "data2"
        mock_func2.assert_called_once()
        mock_func1.assert_not_called()

    def test_fetch_with_fallback_unavailable_source(self):
        """测试不可用数据源被跳过"""
        mock_func1 = Mock(return_value="data1")
        mock_func2 = Mock(return_value="data2")

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        # 标记source1为不可用
        self.fallback._sources["source1"].available = False

        result = self.fallback.fetch_with_fallback()
        assert result == "data2"
        mock_func1.assert_not_called()
        mock_func2.assert_called_once()

    def test_fetch_with_fallback_returns_none(self):
        """测试数据源返回None"""
        mock_func1 = Mock(return_value=None)
        mock_func2 = Mock(return_value="data2")

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        result = self.fallback.fetch_with_fallback()
        assert result == "data2"

    def test_get_status(self):
        """测试获取状态信息"""
        mock_func1 = Mock(return_value="data1")
        mock_func2 = Mock(return_value="data2")

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        status = self.fallback.get_status()
        assert status["name"] == "test"
        assert "source1" in status["sources"]
        assert "source2" in status["sources"]
        assert len(status["available_sources"]) == 2


class TestAsyncDataSourceFallback:
    """异步数据源回退管理器测试"""

    def setup_method(self):
        """测试前重置状态"""
        self.fallback = DataSourceFallback("test_async")

    def test_async_fetch_with_fallback_success_first_source(self):
        """测试异步第一次数据源就成功"""
        async def mock_func1():
            return "data1"

        async def mock_func2():
            return "data2"

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        result = asyncio.get_event_loop().run_until_complete(
            self.fallback.async_fetch_with_fallback()
        )
        assert result == "data1"

    def test_async_fetch_with_fallback_success_second_source(self):
        """测试异步第一次数据源失败，第二次成功"""
        async def mock_func1():
            raise Exception("Source 1 failed")

        async def mock_func2():
            return "data2"

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        result = asyncio.get_event_loop().run_until_complete(
            self.fallback.async_fetch_with_fallback()
        )
        assert result == "data2"

    def test_async_fetch_with_fallback_all_fail(self):
        """测试异步所有数据源都失败"""
        async def mock_func1():
            raise Exception("Source 1 failed")

        async def mock_func2():
            raise Exception("Source 2 failed")

        self.fallback.add_source("source1", mock_func1, DataSourcePriority.PRIMARY)
        self.fallback.add_source("source2", mock_func2, DataSourcePriority.SECONDARY)

        with pytest.raises(Exception) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                self.fallback.async_fetch_with_fallback()
            )

        assert "Source 2 failed" in str(exc_info.value)


class TestPredefinedFallbacks:
    """预定义回退配置测试"""

    def test_stock_quotes_fallback(self):
        """测试股票行情回退配置"""
        fallback = StockQuotesFallback()
        assert fallback.name == "stock_quotes"

    def test_stock_news_fallback(self):
        """测试股票新闻回退配置"""
        fallback = StockNewsFallback()
        assert fallback.name == "stock_news"

    def test_stock_list_fallback(self):
        """测试股票列表回退配置"""
        fallback = StockListFallback()
        assert fallback.name == "stock_list"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
